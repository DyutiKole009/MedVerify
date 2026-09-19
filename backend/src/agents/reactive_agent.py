"""
Reactive Agent — fixed 5-step packaging-photo verification pipeline.

Tool sequence (no model backbone required — order is always the same):
  1. extract_from_image      — Rekognition OCR + regex field extraction
  2. normalize_and_resolve   — OpenSearch fuzzy match against drug index
  3. run_parallel_checks     — DynamoDB: batch + manufacturer + community
  4. synthesize_evidence     — Bedrock narration (falls back to deterministic)
  5. store_session           — persist final result to DynamoDB
"""
from typing import Any, Dict, Optional

from src.tools.reactive_tools import (
    extract_from_image,
    normalize_and_resolve,
    run_parallel_checks,
    synthesize_evidence,
    store_session,
)
from src.utils.logger import logger


def run_reactive_agent(
    image_s3_key: str,
    mime_type: str = "image/jpeg",
    session_id: Optional[str] = None,
    **_kwargs,
) -> Dict[str, Any]:
    """
    Run the full 5-step Reactive pipeline sequentially.
    Each tool's output is passed as input to the next step.
    """
    import uuid
    session_id = session_id or str(uuid.uuid4())

    logger.info(f"[REACTIVE] session={session_id} step=1 extract_from_image")
    extraction = extract_from_image(image_s3_key=image_s3_key, mime_type=mime_type)

    logger.info(f"[REACTIVE] session={session_id} step=2 normalize_and_resolve")
    resolved = normalize_and_resolve(extraction=extraction)

    logger.info(f"[REACTIVE] session={session_id} step=3 run_parallel_checks")
    checks = run_parallel_checks(resolved=resolved)

    logger.info(f"[REACTIVE] session={session_id} step=4 synthesize_evidence")
    synthesis = synthesize_evidence(extraction=extraction, checks=checks)

    logger.info(f"[REACTIVE] session={session_id} step=5 store_session")
    result = {
        "session_id":    session_id,
        "tier":          "REACTIVE",
        "extracted":     extraction,
        "resolved":      resolved,
        "checks":        checks,
        **synthesis,
    }
    store_session(session_id=session_id, result=result)

    logger.info(f"[REACTIVE] session={session_id} DONE bedrock_available={synthesis.get('bedrock_available')}")
    return result