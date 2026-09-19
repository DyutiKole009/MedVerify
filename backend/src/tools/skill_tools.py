"""Deterministic lookup tools used by the Skill Agent."""
from typing import Any, Dict, Optional

from boto3.dynamodb.conditions import Key
from strands import tool

from src.aws_wrappers.dynamodb import DynamoDBWrapper
from src.aws_wrappers.opensearch import OpenSearchWrapper
from src.aws_wrappers.s3 import S3Wrapper
from src.config import settings


@tool
def check_batch(batch_no: str, drug_name: Optional[str] = None, manufacturer: Optional[str] = None) -> Dict[str, Any]:
    """Look up an official batch record and return its community status."""
    database = DynamoDBWrapper()
    if manufacturer:
        manufacturer_id = manufacturer.strip().upper().replace(" ", "#")
        record = database.get_item(settings.DYNAMODB_BATCHES_TABLE, f"BATCH#{batch_no}", f"MFR#{manufacturer_id}")
    else:
        records, _ = database.query(
            settings.DYNAMODB_BATCHES_TABLE,
            Key("PK").eq(f"BATCH#{batch_no}"),
            limit=10,
        )
        record = records[0] if records else None
    if not record:
        return {"found": False, "batch_record": None, "community_flag": False}
    if drug_name and record.get("drug_name_normalized") != drug_name.lower().strip():
        return {"found": False, "batch_record": None, "community_flag": False}
    return {"found": True, "batch_record": record, "community_flag": bool(record.get("community_flag", False))}


@tool
def get_manufacturer_history(manufacturer_name: str) -> Dict[str, Any]:
    """Return the manufacturer record and recent batches from GSI2."""
    database = DynamoDBWrapper()
    manufacturer_id = manufacturer_name.strip().upper().replace(" ", "#")
    manufacturer = database.get_item(settings.DYNAMODB_MANUFACTURERS_TABLE, f"MFR#{manufacturer_id}")
    batches, _ = database.query_gsi(
        settings.DYNAMODB_BATCHES_TABLE, "GSI2", "GSI2PK", f"MFR#{manufacturer_id}",
        sort_key="GSI2SK", sort_begins_with="BATCH#", limit=20, scan_index_forward=False,
    )
    return {"manufacturer_record": manufacturer, "recent_batches": batches}


@tool
def get_notice(source_document_s3_key: str) -> Dict[str, Any]:
    """Fetch a stored regulatory notice from the raw-document bucket."""
    body = S3Wrapper().get_object_bytes(settings.S3_RAW_DOCUMENTS_BUCKET, source_document_s3_key)
    return {"notice_text": body.decode("utf-8", errors="replace"), "source_url": f"s3://{settings.S3_RAW_DOCUMENTS_BUCKET}/{source_document_s3_key}"}


@tool
def get_case_history(session_id: str) -> Dict[str, Any]:
    """Retrieve a previously stored investigation session."""
    return {"session_record": DynamoDBWrapper().get_item(settings.DYNAMODB_SESSIONS_TABLE, f"SESSION#{session_id}", "RESULT")}


@tool
def get_community_reports(batch_no: Optional[str] = None, drug_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve community reports by batch or drug GSI."""
    database = DynamoDBWrapper()
    if batch_no:
        reports, _ = database.query_gsi(settings.DYNAMODB_REPORTS_TABLE, "GSI1", "GSI1PK", f"BATCH#{batch_no}", limit=50)
    elif drug_name:
        reports, _ = database.query_gsi(settings.DYNAMODB_REPORTS_TABLE, "GSI2", "GSI2PK", f"DRUG#{drug_name.lower().strip()}", limit=50)
    else:
        return {"report_count": 0, "reports": [], "community_flag": False}
    return {"report_count": len(reports), "reports": reports, "community_flag": any(report.get("status") == "APPROVED" for report in reports)}


@tool
def search_drug(fuzzy_text: str, size: int = 5) -> Dict[str, Any]:
    """Find likely drug, manufacturer, and batch matches."""
    results = OpenSearchWrapper().search_fuzzy(settings.OPENSEARCH_INDEX_DRUGS, "search_text", fuzzy_text, size=size)
    return {"candidates": [{
        "drug_name": hit.get("source", {}).get("drug_name"),
        "manufacturer": hit.get("source", {}).get("manufacturer_name"),
        "batch_no": hit.get("source", {}).get("batch_no"),
        "score": hit.get("score", 0.0),
    } for hit in results]}


SKILL_TOOLS = [check_batch, get_manufacturer_history, get_notice, get_case_history, get_community_reports, search_drug]