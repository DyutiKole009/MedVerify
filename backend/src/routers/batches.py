"""
Batches and Manufacturers API router (§12.2).
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException

from datetime import datetime, timezone
from src.domain.normalization import normalize_batch_no
from src.tools.skill_tools import check_batch, get_manufacturer_history
from src.tools.aws import get_dynamodb_resource, convert_decimals_to_primitives
from src.pipelines.nsq_ingestion.scraper import scrape_nsq_listing
from src.config import settings
from src.utils.logger import logger

router = APIRouter()


@router.get("/batches/notices/list")
def list_regulatory_notices() -> Dict[str, Any]:
    """
    Retrieves ingested regulatory gazette notices from IngestedDocs table (§5.2).
    """
    documents: List[Dict[str, Any]] = []
    try:
        dynamo = get_dynamodb_resource()
        table = dynamo.Table(settings.DYNAMODB_INGESTED_DOCS_TABLE)
        resp = table.scan(Limit=100)
        for item in resp.get("Items", []):
            item = convert_decimals_to_primitives(item)
            documents.append({
                "id": item.get("PK", ""),
                "month": item.get("source_month", ""),
                "name": item.get("doc_url", "Unknown Document").split("/")[-1],
                "type": item.get("doc_type", "CENTRAL"),
                "batchesFlagged": int(item.get("rows_extracted", 0)),
                "spuriousCount": 0,
                "url": item.get("doc_url", ""),
                "status": "INGESTED" if item.get("parse_status") == "PARSED" else "DISCOVERED_CANDIDATE",
                "docHash": item.get("PK", "").replace("DOC#", ""),
            })
    except Exception as exc:
        logger.warning(f"IngestedDocs scan failed: {exc}. Returning empty list.")

    return {"documents": documents}


@router.post("/batches/notices/scrape")
def trigger_cdsco_scraper() -> Dict[str, Any]:
    """Triggers live web scraping of the CDSCO notifications portal (§5.2)."""
    candidates = scrape_nsq_listing()
    results = []
    for idx, c in enumerate(candidates):
        results.append({
            "id": f"scraped-{idx+1}",
            "month": c.source_month,
            "name": c.title,
            "type": c.doc_type,
            "batchesFlagged": 0,
            "spuriousCount": 0,
            "url": c.doc_url,
            "status": "DISCOVERED_CANDIDATE",
            "docHash": c.doc_hash,
        })
    return {
        "count": len(results),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "candidates": results,
    }


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
