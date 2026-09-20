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
    if not request.batch_no and not request.drug_name and not request.manufacturer:
        raise HTTPException(status_code=400, detail="At least one search parameter (batch_no, drug_name, or manufacturer) is required.")

    normalized_batch = normalize_batch_no(request.batch_no) if request.batch_no else None
    normalized_drug  = normalize_drug_name(request.drug_name) if request.drug_name else None

    # 1. Orchestrator classifies → picks tier
    decision = orchestrate(
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
        batch_no=normalized_batch,
        drug_name=normalized_drug,
        manufacturer_name=request.manufacturer or "",
        session_id=session_id,
    )

    batch_record   = agent_result.get("batch_record")
    community_flag = agent_result.get("community_flag", False)
    status_category = agent_result.get("status_category", "NO_MATCH")

    # 4. Update session record in DynamoDB with completed verification result
    try:
        completed_iso = datetime.now(timezone.utc).isoformat()
        final_summary = agent_result.get("summary") or (
            f"Batch {batch_record['batch_no']} ({batch_record.get('drug_name')}) flagged as {batch_record.get('alert_status')}: {batch_record.get('nsq_reason')}."
            if batch_record
            else f"No official CDSCO regulatory quality failure recorded for batch {normalized_batch or request.drug_name}."
        )
        sessions_table.put_item(Item=convert_floats_to_decimals({
            "PK": f"SESSION#{session_id}",
            "SK": "META",
            "user_id": user["user_id"],
            "mode": "QUICK_CHECK",
            "input_type": "TEXT",
            "drug_name": request.drug_name or (batch_record.get("drug_name") if batch_record else None),
            "batch_no": normalized_batch or (batch_record.get("batch_no") if batch_record else None),
            "status_category": status_category,
            "status": "DONE",
            "summary": final_summary,
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
    )

