"""
Investigation API routers (§12.1 POST /investigate & POST /investigate/deep).
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, Depends, status

from src.models.schemas import (
    InvestigateRequest,
    DeepInvestigateRequest,
    ProcessingResponse,
)
from src.agents.orchestrator import orchestrate
from src.tools.aws import get_dynamodb_resource, convert_floats_to_decimals
from src.dependencies.auth import get_current_user_optional
from src.config import settings

router = APIRouter()


@router.post("", response_model=ProcessingResponse, status_code=status.HTTP_202_ACCEPTED)
def start_reactive_investigation(
    request: InvestigateRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
) -> ProcessingResponse:
    """
    Submits a packaging photo for full reactive verification (§12.1).
    Returns 202 Accepted with a session_id for polling.
    """
    session_id = str(uuid.uuid4())
    decision = orchestrate(has_image=True, image_s3_key=request.image_s3_key)

    now_iso = datetime.now(timezone.utc).isoformat()
    dynamo = get_dynamodb_resource()
    sessions_table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)

    session_item = {
        "PK": f"SESSION#{session_id}",
        "SK": "META",
        "user_id": user["user_id"],
        "mode": "FULL_INVESTIGATION",
        "input_type": "IMAGE",
        "input_data": {
            "image_s3_key": request.image_s3_key,
        },
        "status": "PROCESSING",
        "orchestrator_decision": decision.model_dump(),
        "created_at": now_iso,
    }
    sessions_table.put_item(Item=convert_floats_to_decimals(session_item))

    return ProcessingResponse(
        session_id=session_id,
        status="PROCESSING",
        orchestrator_decision=decision.model_dump(),
    )


@router.post("/deep", response_model=ProcessingResponse, status_code=status.HTTP_202_ACCEPTED)
def start_deep_investigation(
    request: DeepInvestigateRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
) -> ProcessingResponse:
    """
    Submits an open suspicion or ambiguous case for autonomous deep investigation (§12.1).
    Returns 202 Accepted with a session_id for polling.
    """
    session_id = str(uuid.uuid4())
    decision = orchestrate(
        text=request.description,
        drug_name=request.drug_name,
        batch_no=request.batch_no,
        has_image=bool(request.image_s3_key),
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    dynamo = get_dynamodb_resource()
    sessions_table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)

    session_item = {
        "PK": f"SESSION#{session_id}",
        "SK": "META",
        "user_id": user["user_id"],
        "mode": "DEEP_INVESTIGATE",
        "input_type": "TEXT" if not request.image_s3_key else "IMAGE",
        "input_data": {
            "description": request.description,
            "drug_name": request.drug_name,
            "batch_no": request.batch_no,
            "image_s3_key": request.image_s3_key,
        },
        "status": "PROCESSING",
        "orchestrator_decision": decision.model_dump(),
        "created_at": now_iso,
    }
    sessions_table.put_item(Item=convert_floats_to_decimals(session_item))

    return ProcessingResponse(
        session_id=session_id,
        status="PROCESSING",
        orchestrator_decision=decision.model_dump(),
    )
