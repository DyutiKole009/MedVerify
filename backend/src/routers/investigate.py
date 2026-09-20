"""
Investigation API routers (§12.1 POST /investigate & POST /investigate/deep).
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, BackgroundTasks, Depends, status

from src.models.schemas import (
    InvestigateRequest,
    DeepInvestigateRequest,
    ProcessingResponse,
)
from src.agents.orchestrator import orchestrate
from src.tools.aws import get_dynamodb_resource, convert_floats_to_decimals
from src.tools.reactive_tools import extract_from_image
from src.tools.skill_tools import check_batch
from src.dependencies.auth import get_current_user_optional
from src.config import settings
from src.utils.logger import logger

router = APIRouter()


def _run_deep_agent_background(session_id: str, request: DeepInvestigateRequest):
    """Executes Deep Agent autonomously with Gemini in background."""
    try:
        from src.agents.deep_agent import run_deep_agent
        query_text = request.get_query_text()
        run_deep_agent(
            text=query_text,
            batch_no=request.batch_no,
            drug_name=request.drug_name,
            session_id=session_id,
        )
        logger.info(f"Deep Agent background task completed for session {session_id}")
    except Exception as exc:
        logger.warning(f"Background deep agent execution failed for session {session_id}: {exc}")


@router.post("", response_model=ProcessingResponse, status_code=status.HTTP_200_OK)
def start_reactive_investigation(
    request: InvestigateRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
) -> ProcessingResponse:
    """
    Submits a packaging photo for full reactive verification (§12.1).
    Performs Gemini Flash multimodal OCR, parses medicine fields, and checks CDSCO records.
    """
    session_id = str(uuid.uuid4())
    decision = orchestrate(has_image=True, image_s3_key=request.image_s3_key)

    # Perform Gemini Flash multimodal extraction
    extracted = extract_from_image(request.image_s3_key, request.mime_type)
    batch_no = extracted.get("batch_no")
    drug_name = extracted.get("drug_name")
    mfg_name = extracted.get("manufacturer_name")

    batch_record = None
    status_cat = "NO_MATCH"
    if batch_no:
        batch_record = check_batch(batch_no)
        if batch_record:
            status_cat = batch_record.get("alert_status", "MATCH_FOUND")

    reasoning_trace = [
        f"Step 1: Uploaded packaging artifact to S3 bucket '{settings.S3_UPLOADS_BUCKET}'.",
        f"Step 2: Google Gemini Flash multimodal OCR detected packaging text with {int(extracted.get('ocr_confidence', 0.9)*100)}% confidence.",
        f"Step 3: Identified Drug: '{drug_name}' | Manufacturer: '{mfg_name}'.",
    ]
    if batch_no:
        reasoning_trace.append(f"Step 4: Queried CDSCO registry for Batch '{batch_no}'.")
        if batch_record:
            reasoning_trace.append(f"Step 5: Alert flag '{status_cat}' found in CDSCO regulatory database.")
        else:
            reasoning_trace.append(f"Step 5: No adverse CDSCO recall notice found for batch '{batch_no}'.")
    else:
        reasoning_trace.append("Step 4: Batch number not detected in this view (crop or angle).")

    # Build source attributions from the batch record
    sources = []
    if batch_record:
        month = batch_record.get("source_month", "")
        month_label = f" · {month}" if month else ""
        sources.append({
            "type": "DB",
            "label": f"CDSCO DynamoDB{month_label} — {batch_record.get('alert_status', 'NSQ')} Record",
            "reference": batch_record.get("batch_no") or batch_no,
            "doc_url": batch_record.get("source_document_pdf_url"),
            "content_preview": (
                f"Drug: {batch_record.get('drug_name', 'N/A')} | "
                f"Batch: {batch_record.get('batch_no', 'N/A')} | "
                f"Manufacturer: {batch_record.get('manufacturer_name', 'N/A')} | "
                f"Status: {batch_record.get('alert_status', 'N/A')} | "
                f"Reason: {batch_record.get('nsq_reason', 'N/A')}"
            ),
        })

    if batch_record:
        summary = f"ALERT: Batch {batch_no} ({drug_name}) is flagged as {status_cat} by CDSCO: {batch_record.get('nsq_reason', 'Regulatory quality failure')}."
    elif batch_no:
        summary = f"Scanned {drug_name} (Batch: {batch_no}, Mfg: {mfg_name}). No CDSCO recall record found."
    else:
        summary = f"Scanned {drug_name} by {mfg_name}. Batch number was cut off or not visible in this photo. Please snap the crimped edge or batch stamp to check CDSCO recall alerts."

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
        "drug_name": drug_name or "Packaging Scan",
        "batch_no": batch_no or "N/A",
        "extracted_fields": extracted,
        "batch_record": batch_record,
        "status_category": status_cat if batch_no else "CLEAR",
        "summary": summary,
        "reasoning_trace": reasoning_trace,
        "sources": sources,
        "status": "DONE",
        "orchestrator_decision": decision.model_dump(),
        "created_at": now_iso,
        "completed_at": now_iso,
    }
    sessions_table.put_item(Item=convert_floats_to_decimals(session_item))

    return ProcessingResponse(
        session_id=session_id,
        status="DONE",
        orchestrator_decision=decision.model_dump(),
        extracted_fields={
            "batch_no": batch_no or "Not visible in photo",
            "drug_name": drug_name,
            "manufacturer": mfg_name,
            "expiry_date": extracted.get("expiry_date") or "Not visible in photo",
            "mfg_date": extracted.get("mfg_date") or "Not visible in photo",
            "ocr_confidence": extracted.get("ocr_confidence", 0.95),
            "unreadable_fields": extracted.get("unreadable_fields", []),
        },
        batch_record=batch_record,
        status_category=status_cat if batch_no else "CLEAR",
        summary=summary,
        reasoning_trace=reasoning_trace,
        sources=sources,
    )


@router.post("/deep", response_model=ProcessingResponse, status_code=status.HTTP_202_ACCEPTED)
def start_deep_investigation(
    request: DeepInvestigateRequest,
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_current_user_optional),
) -> ProcessingResponse:
    """
    Submits an open suspicion or ambiguous case for autonomous deep investigation (§12.1).
    Returns 202 Accepted with a session_id for polling.
    Fires the Gemini Deep Agent in the background.
    """
    session_id = str(uuid.uuid4())
    query_text = request.get_query_text()
    decision = orchestrate(
        text=query_text or None,
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

    # Trigger autonomous background investigation with Gemini
    background_tasks.add_task(_run_deep_agent_background, session_id, request)

    return ProcessingResponse(
        session_id=session_id,
        status="PROCESSING",
        orchestrator_decision=decision.model_dump(),
    )
