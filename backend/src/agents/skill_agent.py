"""
Skill Agent — dynamic LLM tool-selection agent guided by SKILL.md specifications.
Uses Strands Agent + Groq with CDSCO regulatory lookup tools.
"""
import os
import uuid
import json
from typing import Any, Dict, List, Optional

from src.tools.skill_tools import (
    SKILL_TOOLS,
    check_batch,
    get_community_reports,
    get_manufacturer_history,
    search_drug,
    get_notice,
    get_case_history,
)
from src.tools.skill_docs import build_skills_system_prompt
from src.tools.aws import get_dynamodb_resource, convert_floats_to_decimals
from src.config import settings
from src.utils.logger import logger


def get_skill_strands_agent():
    """
    Returns a Strands Agent configured with Groq and all SKILL_TOOLS.
    The agent's system prompt is loaded directly from all SKILL.md definition files.
    """
    try:
        import openai
        from strands import Agent
        from strands.models.openai import OpenAIModel

        api_key = getattr(settings, "GROQ_API_KEY", None) or os.environ.get("GROQ_API_KEY", "gsk_mock")
        client = openai.Client(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
        )
        model = OpenAIModel(
            client=client,
            model_id=getattr(settings, "GROQ_MODEL_ID", None) or "llama-3.3-70b-versatile",
        )
        system_prompt = build_skills_system_prompt()

        return Agent(
            model=model,
            tools=SKILL_TOOLS,
            system_prompt=system_prompt,
        )
    except Exception as e:
        logger.warning(f"Failed to initialize Strands Skill Agent: {e}")
        return None


def run_skill_agent(
    batch_no: Optional[str] = None,
    drug_name: Optional[str] = None,
    manufacturer_name: Optional[str] = "",
    session_id: Optional[str] = None,
    **_kwargs,
) -> Dict[str, Any]:
    """
    Runs the Skill Agent where the LLM selects the tools to invoke based on SKILL.md rules.
    Falls back gracefully to direct tool invocation on failure or offline execution.
    """
    session_id = session_id or str(uuid.uuid4())

    batch_record = None
    community_flag = False
    community_reports: List[Dict[str, Any]] = []
    mfg_result: Dict[str, Any] = {"manufacturer_record": None, "recent_batches": []}
    summary: Optional[str] = None
    tools_invoked: List[str] = []
    kb_sources: List[Dict[str, Any]] = []  # KB advisory chunks from retrieve_regulatory_advisory

    # Attempt LLM tool selection via Strands Agent
    agent = get_skill_strands_agent()
    if agent and getattr(settings, "GROQ_API_KEY", None):
        try:
            prompt_parts = ["Investigate and verify the following medicine batch details using appropriate tools:"]
            if batch_no:
                prompt_parts.append(f"- Batch Number: {batch_no}")
            if drug_name:
                prompt_parts.append(f"- Drug Name: {drug_name}")
            if manufacturer_name:
                prompt_parts.append(f"- Manufacturer: {manufacturer_name}")
            user_prompt = "\n".join(prompt_parts)

            logger.info(f"[SKILL AGENT] Invoking Strands LLM with dynamic tool selection: {user_prompt}")
            result = agent(user_prompt)

            # Extract message content
            if hasattr(result, "message"):
                msg = result.message
                if isinstance(msg, dict):
                    c = msg.get("content", "")
                    summary = c[0].get("text", "") if isinstance(c, list) and c else str(c)
                else:
                    summary = str(msg)
            elif isinstance(result, str):
                summary = result

            # Parse tool results from agent conversation history
            for message in getattr(agent, "messages", []):
                content_blocks = message.get("content", []) if isinstance(message, dict) else getattr(message, "content", [])
                for block in content_blocks:
                    # Capture tool uses
                    if isinstance(block, dict) and "tool_use" in block:
                        tool_name = block["tool_use"].get("name")
                        if tool_name:
                            tools_invoked.append(tool_name)
                    # Capture tool results
                    if isinstance(block, dict) and "tool_result" in block:
                        tr_content = block["tool_result"].get("content", "")
                        try:
                            parsed_tr = json.loads(tr_content) if isinstance(tr_content, str) else tr_content
                            if isinstance(parsed_tr, dict):
                                if "batch_record" in parsed_tr:
                                    batch_record = parsed_tr.get("batch_record")
                                    community_flag = parsed_tr.get("community_flag", community_flag)
                                if "reports" in parsed_tr:
                                    community_reports = parsed_tr.get("reports", [])
                                    community_flag = parsed_tr.get("community_flag", community_flag)
                                if "manufacturer_record" in parsed_tr:
                                    mfg_result = parsed_tr
                                # Capture KB advisory chunks for source attribution
                                if "results" in parsed_tr and parsed_tr.get("found"):
                                    for kb_item in parsed_tr.get("results", []):
                                        s3_uri = kb_item.get("s3_uri", "")
                                        filename = s3_uri.split("/")[-1] if s3_uri else "advisory"
                                        kb_sources.append({
                                            "type": "KB",
                                            "label": f"Bedrock KB · {filename}",
                                            "reference": s3_uri,
                                            "content_preview": (kb_item.get("content") or "")[:150],
                                            "score": kb_item.get("score"),
                                        })
                        except Exception:
                            pass

            logger.info(f"[SKILL AGENT] LLM completed tool selection: invoked {tools_invoked}")

        except Exception as exc:
            logger.warning(f"[SKILL AGENT] Strands LLM tool execution encountered error: {exc}. Falling back to direct tool lookup.")

    # -- Fallback direct tool execution ------------------------------------------
    # batch_record may have been populated from Strands tool results above;
    # run fallback only when missing.
    if batch_record is None and batch_no:
        batch_result = check_batch(batch_no=batch_no, drug_name=drug_name, manufacturer=manufacturer_name)
        batch_record = batch_result.get("batch_record")
        if not community_flag:
            community_flag = batch_result.get("community_flag", False)

    if not community_reports and (batch_no or drug_name):
        comm_res = get_community_reports(batch_no=batch_no, drug_name=drug_name)
        community_reports = comm_res.get("reports", [])
        if not community_flag:
            community_flag = comm_res.get("community_flag", False)

    if not mfg_result.get("manufacturer_record") and manufacturer_name:
        mfg_result = get_manufacturer_history(manufacturer_name)

    # -- Build source attributions -----------------------------------------------
    sources: List[Dict[str, Any]] = []

    if batch_record:
        month = batch_record.get("source_month", "")
        month_label = f" · {month}" if month else ""
        sources.append({
            "type": "DB",
            "label": f"CDSCO DynamoDB{month_label} — {batch_record.get('alert_status', 'NSQ')} Record",
            "reference": batch_record.get("batch_no") or batch_no,
            "doc_url": batch_record.get("source_document_pdf_url"),
            "content_preview": (
                f"Drug: {batch_record.get('drug_name', 'N/A')} | "
                f"Batch: {batch_record.get('batch_no', 'N/A')} | "
                f"Manufacturer: {batch_record.get('manufacturer_name', 'N/A')} | "
                f"Status: {batch_record.get('alert_status', 'N/A')} | "
                f"Reason: {batch_record.get('nsq_reason', 'N/A')}"
            ),
        })

    # Merge KB sources (deduplicated by reference)
    seen_refs = {s["reference"] for s in sources if s.get("reference")}
    for kb_src in kb_sources:
        if kb_src.get("reference") not in seen_refs:
            sources.append(kb_src)
            seen_refs.add(kb_src.get("reference"))

    # Determine status category based on official and community evidence
    if not batch_record and not community_flag:
        status_category = "NO_MATCH"
    elif batch_record and batch_record.get("alert_status") == "SPURIOUS":
        status_category = "SPURIOUS"
    elif batch_record and batch_record.get("alert_status") == "NSQ":
        status_category = "NSQ"
    elif community_flag:
        status_category = "COMMUNITY_FLAGGED"
    elif batch_record and batch_record.get("alert_status"):
        status_category = batch_record.get("alert_status")
    else:
        status_category = "MATCH_FOUND"

    if not summary:
        summary = (
            f"Regulatory verification for Batch '{batch_no or 'N/A'}': {status_category}. "
            f"Community reports: {len(community_reports)}. "
            f"Absence of an official flag is not proof of safety."
        )

    result_data = {
        "session_id": session_id,
        "tier": "SKILL",
        "status_category": status_category,
        "batch_record": batch_record,
        "community_flag": community_flag,
        "community_reports": community_reports,
        "manufacturer_history": mfg_result,
        "summary": summary,
        "tools_invoked": tools_invoked,
        "limitation_statement": "Absence of a flag is not proof of safety.",
        "sources": sources,
    }

    # Persist session to DynamoDB
    try:
        dynamo = get_dynamodb_resource()
        table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
        table.update_item(
            Key={"PK": f"SESSION#{session_id}", "SK": "META"},
            UpdateExpression="SET final_result = :r, #st = :s",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":r": convert_floats_to_decimals(result_data),
                ":s": "DONE",
            },
        )
    except Exception as exc:
        logger.warning(f"Could not persist skill agent result in DynamoDB: {exc}")

    return result_data
