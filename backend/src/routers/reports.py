"""
Community Reports API router (§12.1 POST /reports & GET /reports).
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.models.schemas import ReportCreateRequest
from src.domain.normalization import normalize_drug_name, normalize_batch_no
from src.tools.skill_tools import get_community_reports
from src.tools.aws import get_dynamodb_resource, convert_floats_to_decimals
from src.dependencies.auth import require_authenticated_user
from src.config import settings

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_report(
    report: ReportCreateRequest,
    user: Dict[str, Any] = Depends(require_authenticated_user),
) -> Dict[str, Any]:
    """
    Submits a community issue report against a batch or drug (§4.2, §12.1).
    Requires Cognito authentication. Generates server-side report_id.
    """
    report_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    normalized_drug = normalize_drug_name(report.drug_name)
    normalized_batch = normalize_batch_no(report.batch_no) if report.batch_no else None

    item: Dict[str, Any] = {
        "PK": f"REPORT#{report_id}",
        "SK": "META",
        "report_id": report_id,
        "drug_name": report.drug_name,
        "drug_name_normalized": normalized_drug,
        "batch_no": normalized_batch,
        "manufacturer_name": report.manufacturer_name,
        "issue_type": report.issue_type,
        "description": report.description,
        "photo_s3_key": report.photo_s3_key,
        "area": report.area,
        "user_id": user["user_id"],
        "status": "PENDING",
        "created_at": now_iso,
    }

    # GSI1: Batch-level aggregation
    if normalized_batch:
        item["GSI1PK"] = f"BATCH#{normalized_batch}"
        item["GSI1SK"] = now_iso

    # GSI2: Drug-level aggregation
    item["GSI2PK"] = f"DRUG#{normalized_drug}"
    item["GSI2SK"] = now_iso

    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_REPORTS_TABLE)
    table.put_item(Item=convert_floats_to_decimals(item))

    return {"report_id": report_id, "status": "PENDING"}


@router.get("")
def list_reports(
    batch_no: Optional[str] = Query(None, description="Batch number to query"),
    drug_name: Optional[str] = Query(None, description="Drug name to query"),
) -> Dict[str, Any]:
    """
    Retrieves community reports for a batch or drug name (§12.1).
    Publicly accessible without authentication.
    """
    if not batch_no and not drug_name:
        raise HTTPException(status_code=400, detail="Either 'batch_no' or 'drug_name' query parameter is required.")

    normalized_batch = normalize_batch_no(batch_no) if batch_no else None
    normalized_drug = normalize_drug_name(drug_name) if drug_name else None

    return get_community_reports(batch_no=normalized_batch, drug_name=normalized_drug)
