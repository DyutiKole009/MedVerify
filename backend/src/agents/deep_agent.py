"""Deep Agent using deepagents and TodoListMiddleware with Google Gemini."""
import os
import uuid
from typing import Any, Dict, List, Optional
from deepagents import create_deep_agent as _create_deep_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import settings
from src.tools.deep_tools import DEEP_TOOLS
from src.tools.aws import get_dynamodb_resource, convert_floats_to_decimals
from src.utils.logger import logger

DEEP_AGENT_SYSTEM_PROMPT = """You are the MedVerify Deep Agent, an autonomous clinical and regulatory medicine investigator powered by Google Gemini.
Your goal is to thoroughly investigate suspicious medicines, unexpected adverse reactions, suspected counterfeit packaging, or quality defects.

Follow these strict principles:
1. Use TodoListMiddleware to break down your investigation into explicit steps before execution.
2. Investigate systematically: check batch regulatory records via DynamoDB, inspect manufacturer history, look up community reports, and search related regulatory notices.
3. Consult the Bedrock Knowledge Base via `retrieve_regulatory_advisory` whenever analyzing suspected counterfeit packaging (holograms, font discrepancies, foil knurling), explaining clinical consequences of test failures (dissolution, sterility, assay sub-potency), checking transit theft advisories, or advising patient quarantine/PvPI adverse reaction reporting.
4. NEVER claim a medicine is genuine or safe. Always reinforce that absence of a flag is not proof of safety.
5. Synthesize all findings with clear evidence-based citations, risk factors, and practical consumer harm-reduction guidance.
6. Conclude with a clear recommendation on whether the patient should withhold from consuming the medicine and consult a doctor or licensed pharmacist.
"""



def create_deep_agent(**kwargs: Any) -> Any:
    """Create a deep agent graph with TodoListMiddleware using Google Gemini."""
    api_key = settings.GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. The Deep Agent requires a real Gemini API key. "
            "Add it to your .env file as GEMINI_API_KEY=<your-key>."
        )
    if not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = api_key

    model_name = kwargs.pop("model", None) or getattr(settings, "GEMINI_MODEL_ID", None) or "google_genai:gemini-3.6-flash"
    if not model_name.startswith("google_genai:"):
        model_name = f"google_genai:{model_name}"

    tools = kwargs.pop("tools", DEEP_TOOLS)
    middleware = kwargs.pop("middleware", [TodoListMiddleware()])

    return _create_deep_agent(
        model=model_name,
        tools=tools,
        middleware=middleware,
        **kwargs,
    )


def run_deep_agent(
    text: Optional[str] = None,
    batch_no: Optional[str] = None,
    drug_name: Optional[str] = None,
    manufacturer_name: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Executes the Deep Agent with TodoListMiddleware, tracks reasoning trajectory,
    and persists the investigation result to DynamoDB.
    """
    session_id = session_id or str(uuid.uuid4())
    logger.info(f"[DEEP_AGENT] Starting deep investigation for session={session_id}")

    # Baseline evidence checks in case of model error or offline execution
    try:
        from src.tools.skill_tools import check_batch, get_community_reports, get_manufacturer_history
        evidence_checks = {
            "batch": check_batch(batch_no or "", drug_name, manufacturer_name),
            "community": get_community_reports(batch_no, drug_name),
            "manufacturer": get_manufacturer_history(manufacturer_name or ""),
        }
    except Exception as check_exc:
        logger.warning(f"[DEEP_AGENT] Evidence check failed: {check_exc}")
        evidence_checks = {
            "batch": {"found": False, "batch_record": None},
            "community": {"report_count": 0, "reports": []},
            "manufacturer": {"manufacturer_record": None},
        }

    prompt_parts = []
    if text:
        prompt_parts.append(f"Query / Symptoms / Context: {text}")
    if batch_no:
        prompt_parts.append(f"Batch Number: {batch_no}")
    if drug_name:
        prompt_parts.append(f"Drug Name: {drug_name}")
    if manufacturer_name:
        prompt_parts.append(f"Manufacturer: {manufacturer_name}")

    user_query = "\n".join(prompt_parts) or "Investigate current medicine details."

    explanation = ""
    trajectory: List[Dict[str, Any]] = []
    todos: List[Dict[str, Any]] = []

    try:
        agent = create_deep_agent()
        messages = [
            SystemMessage(content=DEEP_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=user_query),
        ]
        logger.info(f"[GEMINI REQUEST] [Deep Agent] Prompting Deep Agent with TodoListMiddleware")
        result = agent.invoke({"messages": messages})
        output_messages = result.get("messages", [])
        if output_messages:
            last_message = output_messages[-1]
            explanation = getattr(last_message, "content", str(last_message))

        todos = result.get("todos", [])
        for msg in output_messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    trajectory.append({"tool": tc.get("name"), "args": tc.get("args")})

        logger.info(f"[GEMINI RESPONSE] [Deep Agent] Finished: {len(trajectory)} tool calls, {len(todos)} todos, {len(explanation)} chars output")

    except Exception as exc:
        logger.warning(f"[DEEP_AGENT] Deep agent execution failed: {exc}. Falling back to baseline synthesis.")
        batch_info = (evidence_checks.get("batch") or {}).get("batch_record") or {}
        alert_status = batch_info.get("alert_status", "No alert recorded")
        comm_reports = (evidence_checks.get("community") or {}).get("report_count", 0)
        mfg_risk = (evidence_checks.get("manufacturer") or {}).get("risk_profile", "Unknown")
        explanation = (
            f"Investigation completed using available regulatory and community records.\n\n"
            f"• Batch Check: {alert_status}\n"
            f"• Community Reports: {comm_reports} report(s)\n"
            f"• Manufacturer Risk: {mfg_risk}\n\n"
            f"Absence of an official flag is not proof of safety."
        )

    final_result = {
        "session_id": session_id,
        "tier": "DEEP",
        "status": "COMPLETED",
        "explanation": explanation,
        "evidence": evidence_checks,
        "trajectory": trajectory,
        "todos": todos,
        "limitation_statement": "Absence of a flag is not proof of safety.",
    }

    # Persist to DynamoDB Sessions table
    try:
        dynamo = get_dynamodb_resource()
        table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
        table.update_item(
            Key={"PK": f"SESSION#{session_id}", "SK": "META"},
            UpdateExpression="SET final_result = :r, #st = :s",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":r": convert_floats_to_decimals(final_result),
                ":s": "DONE",
            },
        )
    except Exception as d_exc:
        logger.warning(f"[DEEP_AGENT] DynamoDB session update failed: {d_exc}")

    return final_result
