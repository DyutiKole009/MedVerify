"""
Reactive Agent — LLM dynamically selects and executes verification tools via Strands Agent.
Equipped with OCR, fuzzy resolution, parallel CDSCO checks, and evidence synthesis tools.
"""
import os
import uuid
from typing import Any, Dict, List, Optional

from src.tools.reactive_tools import (
    REACTIVE_TOOLS,
    extract_from_image,
    normalize_and_resolve,
    run_parallel_checks,
    synthesize_evidence,
    store_session,
)
from src.config import settings
from src.utils.logger import logger

REACTIVE_SYSTEM_PROMPT = """You are the MedVerify Reactive Agent, an autonomous medicine verification investigator.
Your goal is to verify medicine packaging photos by dynamically selecting and executing the appropriate tools.

TOOL SELECTION WORKFLOW:
1. ALWAYS start by calling `extract_from_image(image_s3_key=..., mime_type=...)` to perform multimodal OCR.
2. If text is extracted, call `normalize_and_resolve(extraction=...)` to match against the fuzzy drug registry.
3. Call `run_parallel_checks(resolved=...)` to check official batch recalls, community reports, and manufacturer risk.
4. Call `synthesize_evidence(extraction=..., checks=...)` to generate a non-verdict clinical explanation.
5. Finally, call `store_session(session_id=..., result=...)` to persist the completed record.

PRINCIPLES:
- Never declare a medicine safe or genuine.
- Always include: "Absence of a flag is not proof of safety."
"""


def get_reactive_strands_agent():
    """Returns a Strands Agent configured with Groq and all REACTIVE_TOOLS."""
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
        return Agent(
            model=model,
            tools=REACTIVE_TOOLS,
            system_prompt=REACTIVE_SYSTEM_PROMPT,
        )
    except Exception as e:
        logger.warning(f"Failed to initialize Strands Reactive Agent: {e}")
        return None


def run_reactive_agent(
    image_s3_key: str,
    mime_type: str = "image/jpeg",
    session_id: Optional[str] = None,
    **_kwargs,
) -> Dict[str, Any]:
    """
    Executes the Reactive Agent where the LLM selects and invokes the tools dynamically.
    Falls back gracefully to the deterministic sequential pipeline on error.
    """
    session_id = session_id or str(uuid.uuid4())
    logger.info(f"[REACTIVE] Starting reactive verification session={session_id} image={image_s3_key}")

    agent = get_reactive_strands_agent()
    if agent and getattr(settings, "GROQ_API_KEY", None):
        try:
            prompt = (
                f"Verify the medicine packaging image at S3 key '{image_s3_key}' (MIME: {mime_type}). "
                f"Use session_id='{session_id}' to store the result."
            )
            logger.info(f"[REACTIVE] Prompting Strands Agent for dynamic tool execution")
            result = agent(prompt)
            logger.info(f"[REACTIVE] Strands Agent execution completed successfully")

            # Check if store_session was called and session exists in DynamoDB
            from src.tools.aws import get_dynamodb_resource, convert_decimals_to_primitives
            dynamo = get_dynamodb_resource()
            table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
            db_res = table.get_item(Key={"PK": f"SESSION#{session_id}", "SK": "RESULT"})
            if db_res.get("Item"):
                item = convert_decimals_to_primitives(db_res["Item"])
                return item.get("final_result", item)

        except Exception as exc:
            logger.warning(f"[REACTIVE] Strands Agent execution failed: {exc}. Falling back to sequential execution.")

    # Fallback sequential pipeline
    logger.info(f"[REACTIVE] Executing fallback sequential pipeline for session={session_id}")
    extraction = extract_from_image(image_s3_key=image_s3_key, mime_type=mime_type)
    resolved = normalize_and_resolve(extraction=extraction)
    checks = run_parallel_checks(resolved=resolved)
    synthesis = synthesize_evidence(extraction=extraction, checks=checks)

    result_data = {
        "session_id":    session_id,
        "tier":          "REACTIVE",
        "extracted":     extraction,
        "resolved":      resolved,
        "checks":        checks,
        **synthesis,
    }
    store_session(session_id=session_id, result=result_data)
    return result_data
