"""
Batches and Manufacturers API router (§12.2).
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from src.domain.normalization import normalize_batch_no
from src.tools.skill_tools import check_batch, get_manufacturer_history

router = APIRouter()


@router.get("/batches/{batch_no}")
def get_batch_record(batch_no: str) -> Dict[str, Any]:
    """Retrieves direct official records for a specific medicine batch (§12.2)."""
    normalized_batch = normalize_batch_no(batch_no)
    result = check_batch(batch_no=normalized_batch)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=f"No official CDSCO record found for batch {batch_no}")
    return result


@router.get("/manufacturers/{manufacturer_id}")
def get_manufacturer_summary(manufacturer_id: str) -> Dict[str, Any]:
    """Retrieves history and incident counters for a pharmaceutical manufacturer (§12.2)."""
    clean_id = manufacturer_id.replace("_", " ")
    result = get_manufacturer_history(manufacturer_name=clean_id)
    return result
