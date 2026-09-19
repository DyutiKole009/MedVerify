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
    get_rekognition_client,
    convert_floats_to_decimals,
    opensearch_search,
)
from src.tools.skill_tools import check_batch, get_community_reports, get_manufacturer_history

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


def _clean_json_markdown(raw_text: str) -> str:
    """Strips markdown code blocks like ```json ... ``` from model outputs."""
    text = raw_text.strip()
    match = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if match:
        return match.group(1).strip()
    return text


@tool
def extract_from_image(image_s3_key: str, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """Extract medicine fields from packaging photo using Amazon Rekognition OCR and regex heuristics."""
    rek = get_rekognition_client()
    try:
        response = rek.detect_text(
            Image={"S3Object": {"Bucket": settings.S3_UPLOADS_BUCKET, "Name": image_s3_key}}
        )
    except Exception as e:
        # Fallback to reading image bytes directly
        s3 = get_s3_client()
        image_bytes = s3.get_object(Bucket=settings.S3_UPLOADS_BUCKET, Key=image_s3_key)["Body"].read()
        response = rek.detect_text(Image={"Bytes": image_bytes})

    detections = response.get("TextDetections", [])
    lines = [d["DetectedText"] for d in detections if d.get("Type") == "LINE"]
    confidences = [d.get("Confidence", 90.0) for d in detections if d.get("Type") == "LINE"]

    avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.90
    full_text = " \n ".join(lines)

    # 1. Batch No
    batch_match = re.search(
        r"(?:B\.?\s*No\.?|Batch(?:\s*No\.?)?|Lot(?:\s*No\.?)?|B\.N\.)[\s.:-]*([A-Za-z0-9/-]{3,20})",
        full_text,
        re.IGNORECASE,
    )
    batch_no = batch_match.group(1).strip() if batch_match else None

    # 2. Expiry Date
    exp_match = re.search(
        r"(?:EXP\.?(?:\s*DATE)?|Expiry(?:\s*Date)?)[\s.:-]*([A-Za-z]{3}[.\s/-]*[0-9]{2,4}|[0-9]{1,2}[/-][0-9]{2,4})",
        full_text,
        re.IGNORECASE,
    )
    expiry_date = exp_match.group(1).strip() if exp_match else None

    # 3. Mfg Date
    mfd_match = re.search(
        r"(?:MFD\.?(?:\s*DATE)?|Mfg(?:\s*Date)?)[\s.:-]*([A-Za-z]{3}[.\s/-]*[0-9]{2,4}|[0-9]{1,2}[/-][0-9]{2,4})",
        full_text,
        re.IGNORECASE,
    )
    mfg_date = mfd_match.group(1).strip() if mfd_match else None

    # 4. Brand Name
    detected_brand = None
    for l in lines:
        for b in BRAND_TO_MFG:
            if b in l.upper():
                detected_brand = l.strip()
                break
        if detected_brand:
            break

    # 5. Generic / Formulation
    composition_candidates = []
    for l in lines:
        lower = l.lower()
        if any(ig in lower for ig in ["dosage", "store", "contains", "reach of", "warning", "keep", "dreamstime", "below", "daily", "maximum", "upto", "physician", "cause", "damage", "divided", "dose", "adults"]):
            continue
        if any(kw in lower for kw in ["tablets", "capsules", "suspension", "syrup", "ointment", " ip", " bp", " usp"]):
            composition_candidates.append(l.strip())

    best_comp = max(composition_candidates, key=len) if composition_candidates else None

    final_drug = detected_brand or best_comp or (lines[0] if lines else "Unknown Medicine")
    if detected_brand and best_comp and detected_brand.lower() not in best_comp.lower():
        final_drug = f"{detected_brand} ({best_comp})"

    # 6. Manufacturer
    mfg = None
    mfg_match = re.search(
        r"(?:Mfg\.?\s*(?:by|in)?|Marketed\s*by|Manufactured\s*by)[\s.:-]*([A-Za-z\s.,&]+?(?:Ltd|Limited|Laboratories|Pharma|Pvt|Inc))",
        full_text,
        re.IGNORECASE,
    )
    if mfg_match:
        mfg = mfg_match.group(1).strip()
    else:
        for km in KNOWN_MANUFACTURERS:
            if re.search(r"\b" + re.escape(km) + r"\b", full_text, re.IGNORECASE):
                mfg = km
                break
        if not mfg and detected_brand:
            for b, m in BRAND_TO_MFG.items():
                if b in detected_brand.upper():
                    mfg = m
                    break

    unreadable = []
    if not batch_no:
        unreadable.append("batch_no")
    if not expiry_date:
        unreadable.append("expiry_date")
    if not mfg:
        unreadable.append("manufacturer")

    confidence_label = "high" if avg_conf > 0.85 else ("medium" if avg_conf > 0.70 else "low")

    return {
        "drug_name": final_drug,
        "batch_no": batch_no,
        "manufacturer_name": mfg or "Not detected in photo",
        "mfg_date": mfg_date,
        "expiry_date": expiry_date,
        "confidence": confidence_label,
        "ocr_confidence": round(avg_conf, 2),
        "raw_lines": lines,
        "unreadable_fields": unreadable,
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


def _build_deterministic_explanation(extraction: Dict[str, Any], checks: Dict[str, Any]) -> str:
    """Build a plain-text summary from evidence data without calling Bedrock."""
    drug = extraction.get("drug_name", "Unknown Medicine")
    batch = extraction.get("batch_no", "N/A")
    mfg = extraction.get("manufacturer_name", "Not detected")
    expiry = extraction.get("expiry_date", "N/A")

    batch_status = checks.get("batch", {})
    mfg_status = checks.get("manufacturer", {})
    community_status = checks.get("community", {})

    nsq_flag = batch_status.get("nsq_alert") or batch_status.get("status") == "NSQ"
    spurious_flag = batch_status.get("spurious_alert")
    community_reports = community_status.get("report_count", 0)
    mfg_risk = mfg_status.get("risk_profile", "Unknown")

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

    try:
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
            "bedrock_available": True,
        }
    except Exception as exc:
        # Bedrock unavailable (auth, quota, region) — return deterministic summary so the
        # pipeline can still complete and store a usable result.
        return {
            "explanation": _build_deterministic_explanation(extraction, checks),
            "evidence": checks,
            "limitation_statement": "Absence of a flag is not proof of safety.",
            "bedrock_available": False,
            "bedrock_error": str(exc),
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