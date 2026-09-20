"""
Quick Check API router (§12.1 POST /check).
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from src.models.schemas import CheckRequest, CheckResponse
from src.agents.orchestrator import orchestrate
from src.agents import dispatch
from src.tools.aws import get_dynamodb_resource, convert_floats_to_decimals
from src.domain.normalization import normalize_batch_no, normalize_drug_name
from src.dependencies.auth import get_current_user_optional
from src.config import settings

router = APIRouter()


@router.post("", response_model=CheckResponse)
def run_quick_check(
    request: CheckRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
) -> CheckResponse:
    """
    Executes a Quick Check on a batch number, drug name, or manufacturer.
    No authentication required. Always returns the limitation statement.
    """
    raw_text = (request.text or "").strip()
    symptom_keywords = ["hurt", "pain", "headache", "fever", "nausea", "vomit", "dizzy", "medicine", "pill", "took", "had a", "feel", "sick"]
    
    # If drug_name is actually a full sentence / symptom description, treat as narrative text
    normalized_drug = normalize_drug_name(request.drug_name) if request.drug_name else None
    if normalized_drug and any(k in normalized_drug.lower() for k in symptom_keywords) and len(normalized_drug.split()) > 2:
        if not raw_text:
            raw_text = request.drug_name or normalized_drug
        normalized_drug = None

    normalized_batch = normalize_batch_no(request.batch_no) if request.batch_no else None

    if not normalized_batch and not normalized_drug and not request.manufacturer and not raw_text:
        raise HTTPException(status_code=400, detail="At least one search parameter (batch_no, drug_name, manufacturer, or text query) is required.")

    # 1. Orchestrator classifies → picks tier
    decision = orchestrate(
        text=raw_text or None,
        batch_no=normalized_batch,
        drug_name=normalized_drug,
        manufacturer=request.manufacturer,
        has_image=False,
    )

    session_id = str(uuid.uuid4())
    now_iso    = datetime.now(timezone.utc).isoformat()

    # 2. Create session META record before dispatch
    dynamo         = get_dynamodb_resource()
    sessions_table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
    sessions_table.put_item(Item=convert_floats_to_decimals({
        "PK":                   f"SESSION#{session_id}",
        "SK":                   "META",
        "user_id":              user["user_id"],
        "mode":                 "QUICK_CHECK",
        "input_type":           "TEXT",
        "input_data":           {
            "text":         raw_text or None,
            "batch_no":     normalized_batch,
            "drug_name":    normalized_drug,
            "manufacturer": request.manufacturer,
        },
        "orchestrator_decision": decision.model_dump(),
        "status":               "PROCESSING",
        "created_at":           now_iso,
    }))

    # 3. Dispatch to the agent selected by the orchestrator
    agent_result = dispatch(
        decision,
        text=raw_text or None,
        batch_no=normalized_batch,
        drug_name=normalized_drug,
        manufacturer_name=request.manufacturer or "",
        session_id=session_id,
    )

    batch_record   = agent_result.get("batch_record")
    community_flag = agent_result.get("community_flag", False)
    status_category = agent_result.get("status_category") or ("MATCH_FOUND" if batch_record else "NO_MATCH")
    final_summary = agent_result.get("summary") or (
        f"Batch {batch_record['batch_no']} ({batch_record.get('drug_name')}) flagged as {batch_record.get('alert_status')}: {batch_record.get('nsq_reason')}."
        if batch_record
        else (
            f"No official CDSCO regulatory quality failure recorded for batch {normalized_batch or normalized_drug}."
            if (normalized_batch or normalized_drug)
            else "Investigation completed for reported clinical query."
        )
    )
    explanation = agent_result.get("explanation")
    todos = agent_result.get("todos")
    reasoning_trace = agent_result.get("reasoning_trace")
    extracted_fields = agent_result.get("extracted_fields")
    sources = agent_result.get("sources") or []

    # 4. Update session record in DynamoDB with completed verification result
    try:
        completed_iso = datetime.now(timezone.utc).isoformat()
        sessions_table.put_item(Item=convert_floats_to_decimals({
            "PK": f"SESSION#{session_id}",
            "SK": "META",
            "user_id": user["user_id"],
            "mode": "QUICK_CHECK",
            "input_type": "TEXT",
            "drug_name": normalized_drug or (batch_record.get("drug_name") if batch_record else None),
            "batch_no": normalized_batch or (batch_record.get("batch_no") if batch_record else None),
            "status_category": status_category,
            "status": "DONE",
            "summary": final_summary,
            "explanation": explanation,
            "final_result": agent_result,
            "batch_record": batch_record,
            "orchestrator_decision": decision.model_dump(),
            "created_at": now_iso,
            "completed_at": completed_iso,
        }))
    except Exception as exc:
        pass

    return CheckResponse(
        session_id=session_id,
        status_category=status_category,
        batch_record=batch_record,
        community_flag=community_flag,
        orchestrator_decision=decision.model_dump(),
        limitation_statement="Absence of a flag is not proof of safety.",
        summary=final_summary,
        explanation=explanation,
        reasoning_trace=reasoning_trace,
        todos=todos,
        extracted_fields=extracted_fields,
        sources=sources,
    )

