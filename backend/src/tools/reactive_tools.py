"""Fixed-step tools used by the Reactive Agent."""
import json
import re
from typing import Any, Dict

try:
    from strands import tool
except ImportError:
    def tool(func):
        return func

from src.config import settings
from src.tools.aws import (
    get_dynamodb_resource,
    get_s3_client,
    get_bedrock_runtime_client,
    convert_floats_to_decimals,
    opensearch_search,
)
from src.tools.skill_tools import check_batch, get_community_reports, get_manufacturer_history


def _clean_json_markdown(raw_text: str) -> str:
    """Strips markdown code blocks like ```json ... ``` from model outputs."""
    text = raw_text.strip()
    match = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if match:
        return match.group(1).strip()
    return text


@tool
def extract_from_image(image_s3_key: str, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """Extract medicine fields from a packaging image in S3 using Bedrock vision."""
    s3 = get_s3_client()
    image_bytes = s3.get_object(Bucket=settings.S3_UPLOADS_BUCKET, Key=image_s3_key)["Body"].read()

    fmt = "jpeg"
    if "png" in mime_type.lower():
        fmt = "png"
    elif "webp" in mime_type.lower():
        fmt = "webp"
    elif "gif" in mime_type.lower():
        fmt = "gif"

    prompt = (
        "Analyze this medicine packaging image. Extract the following fields as valid JSON: "
        "drug_name, batch_no, manufacturer_name, mfg_date, expiry_date, confidence (high/medium/low), "
        "and unreadable_fields (list of field names)."
    )

    messages = [{
        "role": "user",
        "content": [
            {"image": {"format": fmt, "source": {"bytes": image_bytes}}},
            {"text": prompt}
        ]
    }]

    bedrock = get_bedrock_runtime_client()
    response = bedrock.converse(
        modelId=settings.BEDROCK_VISION_MODEL_ID,
        messages=messages,
        inferenceConfig={"maxTokens": 2048, "temperature": 0.0},
    )

    raw_text = response.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "{}")
    cleaned = _clean_json_markdown(raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw_text": raw_text, "confidence": "low", "unreadable_fields": ["parsing_error"]}


@tool
def normalize_and_resolve(extraction: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve extracted medicine text against the fuzzy drug index."""
    query_text = " ".join(
        str(extraction.get(f, ""))
        for f in ("drug_name", "manufacturer_name", "batch_no")
        if extraction.get(f)
    )
    query = {
        "size": 5,
        "query": {
            "fuzzy": {
                "search_text": {
                    "value": query_text,
                    "fuzziness": "AUTO",
                    "prefix_length": 1
                }
            }
        }
    }
    hits = opensearch_search(settings.OPENSEARCH_INDEX_DRUGS, query)
    candidates = [
        {
            "drug_name": h.get("_source", {}).get("drug_name"),
            "manufacturer": h.get("_source", {}).get("manufacturer_name"),
            "batch_no": h.get("_source", {}).get("batch_no"),
            "score": h.get("_score", 0.0),
        }
        for h in hits
    ]
    return {
        "extraction": extraction,
        "candidates": candidates,
        "resolved": candidates[0] if candidates else None,
    }


@tool
def run_parallel_checks(resolved: Dict[str, Any]) -> Dict[str, Any]:
    """Run the three independent evidence lookups for a resolved medicine."""
    extraction = resolved.get("extraction", {})
    return {
        "batch": check_batch(
            extraction.get("batch_no", ""),
            extraction.get("drug_name"),
            extraction.get("manufacturer_name"),
        ),
        "manufacturer": get_manufacturer_history(extraction.get("manufacturer_name", "")),
        "community": get_community_reports(
            extraction.get("batch_no"),
            extraction.get("drug_name"),
        ),
    }


@tool
def synthesize_evidence(extraction: Dict[str, Any], checks: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a sourced, non-verdict explanation from extracted evidence."""
    prompt = (
        "Explain only official and community evidence for this medicine. "
        "Never claim a medicine is genuine or safe. "
        "Always state that absence of a flag is not proof of safety."
    )
    messages = [{
        "role": "user",
        "content": [{"text": json.dumps({"extraction": extraction, "checks": checks})}]
    }]

    bedrock = get_bedrock_runtime_client()
    response = bedrock.converse(
        modelId=settings.BEDROCK_SYNTHESIS_MODEL_ID,
        messages=messages,
        system=[{"text": prompt}],
        inferenceConfig={"maxTokens": 2048, "temperature": 0.0},
    )
    result = response.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
    return {
        "explanation": result,
        "evidence": checks,
        "limitation_statement": "Absence of a flag is not proof of safety.",
    }


@tool
def store_session(session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Store a completed Reactive Agent result."""
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
    item = {
        "PK": f"SESSION#{session_id}",
        "SK": "RESULT",
        "session_id": session_id,
        "final_result": result,
        "partial": False,
    }
    table.put_item(Item=convert_floats_to_decimals(item))
    return result


REACTIVE_TOOLS = [extract_from_image, normalize_and_resolve, run_parallel_checks, synthesize_evidence, store_session]