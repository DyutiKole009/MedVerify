"""Fixed-step tools used by the Reactive Agent."""
import json
from typing import Any, Dict

from strands import tool
from src.aws_wrappers.bedrock_runtime import BedrockRuntimeWrapper
from src.aws_wrappers.dynamodb import DynamoDBWrapper
from src.aws_wrappers.opensearch import OpenSearchWrapper
from src.aws_wrappers.s3 import S3Wrapper
from src.config import settings
from src.tools.skill_tools import check_batch, get_community_reports, get_manufacturer_history


@tool
def extract_from_image(image_s3_key: str, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """Extract medicine fields from a packaging image in S3."""
    image = S3Wrapper().get_object_bytes(settings.S3_UPLOADS_BUCKET, image_s3_key)
    return BedrockRuntimeWrapper().extract_from_image(
        settings.BEDROCK_VISION_MODEL_ID, image, mime_type,
        "Return JSON with drug_name, batch_no, manufacturer_name, mfg_date, expiry_date, confidence, and unreadable_fields.",
    )


@tool
def normalize_and_resolve(extraction: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve extracted medicine text against the fuzzy drug index."""
    query = " ".join(str(extraction.get(field, "")) for field in ("drug_name", "manufacturer_name", "batch_no") if extraction.get(field))
    candidates = OpenSearchWrapper().search_fuzzy(settings.OPENSEARCH_INDEX_DRUGS, "search_text", query)
    return {"extraction": extraction, "candidates": candidates, "resolved": candidates[0] if candidates else None}


@tool
def run_parallel_checks(resolved: Dict[str, Any]) -> Dict[str, Any]:
    """Run the three independent evidence lookups for a resolved medicine."""
    extraction = resolved.get("extraction", {})
    return {
        "batch": check_batch(extraction.get("batch_no", ""), extraction.get("drug_name"), extraction.get("manufacturer_name")),
        "manufacturer": get_manufacturer_history(extraction.get("manufacturer_name", "")),
        "community": get_community_reports(extraction.get("batch_no"), extraction.get("drug_name")),
    }


@tool
def synthesize_evidence(extraction: Dict[str, Any], checks: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a sourced, non-verdict explanation from extracted evidence."""
    result = BedrockRuntimeWrapper().converse(
        settings.BEDROCK_SYNTHESIS_MODEL_ID,
        [{"role": "user", "content": [{"text": json.dumps({"extraction": extraction, "checks": checks})}]}],
        "Explain only official and community evidence. Never claim a medicine is genuine or safe. Include: absence of a flag is not proof of safety.",
    )
    return {"explanation": result, "evidence": checks, "limitation_statement": "Absence of a flag is not proof of safety."}


@tool
def store_session(session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Store a completed Reactive Agent result."""
    DynamoDBWrapper().put_item(settings.DYNAMODB_SESSIONS_TABLE, {
        "PK": f"SESSION#{session_id}", "SK": "RESULT", "session_id": session_id, "final_result": result, "partial": False,
    })
    return result


REACTIVE_TOOLS = [extract_from_image, normalize_and_resolve, run_parallel_checks, synthesize_evidence, store_session]