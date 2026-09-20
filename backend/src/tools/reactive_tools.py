"""Fixed-step tools used by the Reactive Agent."""
import json
import re
from typing import Any, Dict, List, Optional

try:
    from strands import tool
except ImportError:
    def tool(func):
        return func

from src.config import settings
from src.tools.aws import (
    get_dynamodb_resource,
    get_s3_client,
    convert_floats_to_decimals,
    opensearch_search,
)
from src.tools.skill_tools import check_batch, get_community_reports, get_manufacturer_history
from src.utils.logger import logger

KNOWN_MANUFACTURERS = [
    "Cipla", "Sun Pharma", "Micro Labs", "Alkem", "Dr. Reddy", "Lupin",
    "Torrent", "Mankind", "Abbott", "GlaxoSmithKline", "GSK", "Zydus",
    "Glenmark", "Intas", "Pfizer", "Sanofi", "Aurobindo", "Macleods", "Aristo", "FDC"
]

BRAND_TO_MFG = {
    "PARACIP": "Cipla Ltd",
    "DOLO": "Micro Labs Ltd",
    "CALPOL": "GlaxoSmithKline Pharmaceuticals",
    "PAN": "Alkem Laboratories",
    "AUGMENTIN": "GlaxoSmithKline Pharmaceuticals",
    "AZITHRAL": "Alembic Pharmaceuticals",
    "TELMA": "Glenmark Pharmaceuticals",
    "MONTEK": "Sun Pharma Laboratories",
    "CLAVAM": "Alkem Laboratories",
    "METOGYL": "J.B. Chemicals & Pharmaceuticals",
}

EXTRACTION_SYSTEM_PROMPT = """You are a pharmaceutical packaging OCR specialist.
Extract all medicine details from the packaging image provided.
Return ONLY valid JSON with these exact fields:
{
  "drug_name": "string or null",
  "batch_no": "string or null",
  "manufacturer_name": "string or null",
  "mfg_date": "string or null",
  "expiry_date": "string or null",
  "confidence": "high|medium|low",
  "ocr_confidence": float between 0.0 and 1.0,
  "raw_lines": ["array", "of", "text", "lines"],
  "unreadable_fields": ["list of field names that could not be read"]
}
Never guess. If a field is not visible, set it to null and add its name to unreadable_fields."""


def _clean_json_markdown(raw_text: str) -> str:
    """Strips markdown code blocks like ```json ... ``` from model outputs."""
    text = raw_text.strip()
    match = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if match:
        return match.group(1).strip()
    return text


def _get_gemini_client():
    """Returns an initialised google.genai Client using GEMINI_API_KEY."""
    from google import genai
    api_key = settings.GEMINI_API_KEY
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client()


def _get_groq_client():
    """Returns an initialised Groq client using GROQ_API_KEY."""
    from groq import Groq
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set.")
    return Groq(api_key=api_key)


@tool
def extract_from_image(image_s3_key: str, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """
    Extract medicine fields from a packaging photo using Gemini Flash multimodal OCR.
    Downloads the image from S3 then passes raw bytes + extraction prompt to Gemini.
    """
    # Download image bytes from S3
    try:
        s3 = get_s3_client()
        image_bytes = s3.get_object(
            Bucket=settings.S3_UPLOADS_BUCKET, Key=image_s3_key
        )["Body"].read()
    except Exception as s3_exc:
        logger.warning(f"[OCR] S3 download failed for {image_s3_key}: {s3_exc}")
        return {
            "drug_name": "Unknown Medicine",
            "batch_no": None,
            "manufacturer_name": "Not detected in photo",
            "mfg_date": None,
            "expiry_date": None,
            "confidence": "low",
            "ocr_confidence": 0.0,
            "raw_lines": [],
            "unreadable_fields": ["image_source", "batch_no", "expiry_date", "manufacturer"],
            "error": str(s3_exc),
        }

    model_id = settings.GEMINI_MODEL_ID or "gemini-2.5-flash"
    logger.info(f"[GEMINI REQUEST] [Multimodal OCR] Model='{model_id}' ImageBytes={len(image_bytes)} MimeType='{mime_type}'")

    try:
        from google.genai import types
        client = _get_gemini_client()
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type or "image/jpeg")
        response = client.models.generate_content(
            model=model_id,
            contents=[
                part,
                "Inspect this pharmaceutical packaging photo and extract all medicine details.",
            ],
            config=types.GenerateContentConfig(
                system_instruction=EXTRACTION_SYSTEM_PROMPT,
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )
        cleaned = _clean_json_markdown(response.text or "{}")
        data = json.loads(cleaned)

        drug_name   = data.get("drug_name") or "Unknown Medicine"
        batch_no    = data.get("batch_no")
        mfg         = data.get("manufacturer_name") or "Not detected in photo"
        mfg_date    = data.get("mfg_date")
        exp_date    = data.get("expiry_date")
        raw_lines   = data.get("raw_lines") or []
        unreadable  = data.get("unreadable_fields") or []

        if not batch_no and "batch_no" not in unreadable:
            unreadable.append("batch_no")
        if not exp_date and "expiry_date" not in unreadable:
            unreadable.append("expiry_date")

        ocr_conf = float(data.get("ocr_confidence", 0.90))
        conf_label = data.get("confidence") or (
            "high" if batch_no and drug_name != "Unknown Medicine" else "medium"
        )

        logger.info(f"[GEMINI RESPONSE] [Multimodal OCR] Drug='{drug_name}' Batch='{batch_no}' Mfg='{mfg}' Confidence={ocr_conf}")
        return {
            "drug_name": drug_name,
            "batch_no": batch_no,
            "manufacturer_name": mfg,
            "mfg_date": mfg_date,
            "expiry_date": exp_date,
            "confidence": conf_label,
            "ocr_confidence": ocr_conf,
            "raw_lines": raw_lines,
            "unreadable_fields": unreadable,
            "gemini_available": True,
        }
    except Exception as exc:
        logger.warning(f"Gemini multimodal OCR failed: {exc}. Returning low-confidence fallback.")
        return {
            "drug_name": "Unknown Medicine",
            "batch_no": None,
            "manufacturer_name": "Not detected in photo",
            "mfg_date": None,
            "expiry_date": None,
            "confidence": "low",
            "ocr_confidence": 0.50,
            "raw_lines": [],
            "unreadable_fields": ["batch_no", "expiry_date", "manufacturer"],
            "error": str(exc),
        }


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
                    "prefix_length": 1,
                }
            }
        },
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


def _build_deterministic_explanation(extraction: Dict[str, Any], checks: Dict[str, Any]) -> str:
    """Build a plain-text summary from evidence data without calling any model."""
    drug   = extraction.get("drug_name", "Unknown Medicine")
    batch  = extraction.get("batch_no", "N/A")
    mfg    = extraction.get("manufacturer_name", "Not detected")
    expiry = extraction.get("expiry_date", "N/A")

    batch_status     = checks.get("batch", {})
    mfg_status       = checks.get("manufacturer", {})
    community_status = checks.get("community", {})

    nsq_flag         = batch_status.get("nsq_alert") or batch_status.get("status") == "NSQ"
    spurious_flag    = batch_status.get("spurious_alert")
    community_reports = community_status.get("report_count", 0)
    mfg_risk         = mfg_status.get("risk_profile", "Unknown")

    lines = [
        f"Medicine: {drug}",
        f"Batch No: {batch} | Manufacturer: {mfg} | Expiry: {expiry}",
        "",
        "Regulatory Evidence (CDSCO):",
    ]
    if nsq_flag:
        lines.append("  \u26a0 NSQ (Not of Standard Quality) alert found for this batch.")
    elif spurious_flag:
        lines.append("  \u26a0 Spurious drug alert found for this batch.")
    else:
        lines.append("  No NSQ or spurious alert found for this batch in the CDSCO database.")

    lines += [
        "",
        f"Manufacturer Risk Profile: {mfg_risk}",
        f"Community Reports: {community_reports} report(s) found for this batch/drug.",
        "",
        "IMPORTANT: Absence of a regulatory flag is NOT proof that this medicine is genuine or safe.",
        "Always consult a licensed pharmacist or healthcare professional.",
    ]
    return "\n".join(lines)


@tool
def synthesize_evidence(extraction: Dict[str, Any], checks: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a sourced, non-verdict plain-language explanation from extracted evidence.
    Uses Groq (fast LLM) to narrate findings; falls back to deterministic text if Groq fails.
    """
    system_prompt = (
        "Explain only official and community evidence for this medicine. "
        "Never claim a medicine is genuine or safe. "
        "Always state that absence of a flag is not proof of safety."
    )
    user_content = json.dumps({"extraction": extraction, "checks": checks})
    model = settings.GROQ_MODEL_ID or "llama-3.3-70b-versatile"
    logger.info(f"[GROQ REQUEST] [Evidence Synthesis] Model='{model}' Prompting clinical & regulatory evidence synthesis")

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=2048,
        )
        result = response.choices[0].message.content or ""
        logger.info(f"[GROQ RESPONSE] [Evidence Synthesis] Synthesis generated: {len(result)} chars")
        return {
            "explanation": result,
            "evidence": checks,
            "limitation_statement": "Absence of a flag is not proof of safety.",
            "groq_available": True,
        }
    except Exception as exc:
        logger.warning(f"Groq synthesis failed: {exc}. Using deterministic fallback.")
        return {
            "explanation": _build_deterministic_explanation(extraction, checks),
            "evidence": checks,
            "limitation_statement": "Absence of a flag is not proof of safety.",
            "groq_available": False,
            "groq_error": str(exc),
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
