"""Deterministic lookup tools used by the Skill Agent."""
from typing import Any, Dict, Optional

from boto3.dynamodb.conditions import Key
try:
    from strands import tool
except ImportError:
    def tool(func):
        return func

from src.config import settings
from src.tools.aws import (
    get_dynamodb_resource,
    get_s3_client,
    convert_decimals_to_primitives,
    opensearch_search,
)


@tool
def check_batch(batch_no: str, drug_name: Optional[str] = None, manufacturer: Optional[str] = None) -> Dict[str, Any]:
    """Look up an official batch record and return its community status."""
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_BATCHES_TABLE)

    if manufacturer:
        manufacturer_id = manufacturer.strip().upper().replace(" ", "#")
        response = table.get_item(Key={"PK": f"BATCH#{batch_no}", "SK": f"MFR#{manufacturer_id}"})
        record = response.get("Item")
    else:
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"BATCH#{batch_no}"),
            Limit=10,
        )
        items = response.get("Items", [])
        record = items[0] if items else None

    if not record:
        return {"found": False, "batch_record": None, "community_flag": False}

    record = convert_decimals_to_primitives(record)
    if drug_name and record.get("drug_name_normalized") != drug_name.lower().strip():
        return {"found": False, "batch_record": None, "community_flag": False}

    return {"found": True, "batch_record": record, "community_flag": bool(record.get("community_flag", False))}


@tool
def get_manufacturer_history(manufacturer_name: str) -> Dict[str, Any]:
    """Return the manufacturer record and recent batches from GSI2."""
    dynamo = get_dynamodb_resource()
    mfr_table = dynamo.Table(settings.DYNAMODB_MANUFACTURERS_TABLE)
    batches_table = dynamo.Table(settings.DYNAMODB_BATCHES_TABLE)

    manufacturer_id = manufacturer_name.strip().upper().replace(" ", "#")
    mfr_res = mfr_table.get_item(Key={"PK": f"MFR#{manufacturer_id}"})
    manufacturer = convert_decimals_to_primitives(mfr_res.get("Item")) if mfr_res.get("Item") else None

    batches_res = batches_table.query(
        IndexName="GSI2",
        KeyConditionExpression=Key("GSI2PK").eq(f"MFR#{manufacturer_id}") & Key("GSI2SK").begins_with("BATCH#"),
        Limit=20,
        ScanIndexForward=False,
    )
    batches = [convert_decimals_to_primitives(item) for item in batches_res.get("Items", [])]

    return {"manufacturer_record": manufacturer, "recent_batches": batches}


@tool
def get_notice(source_document_s3_key: str) -> Dict[str, Any]:
    """Fetch a stored regulatory notice from the raw-document bucket."""
    s3 = get_s3_client()
    response = s3.get_object(Bucket=settings.S3_RAW_DOCUMENTS_BUCKET, Key=source_document_s3_key)
    body = response["Body"].read()
    return {
        "notice_text": body.decode("utf-8", errors="replace"),
        "source_url": f"s3://{settings.S3_RAW_DOCUMENTS_BUCKET}/{source_document_s3_key}",
    }


@tool
def get_case_history(session_id: str) -> Dict[str, Any]:
    """Retrieve a previously stored investigation session."""
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
    res = table.get_item(Key={"PK": f"SESSION#{session_id}", "SK": "RESULT"})
    session_record = convert_decimals_to_primitives(res.get("Item")) if res.get("Item") else None
    return {"session_record": session_record}


@tool
def get_community_reports(batch_no: Optional[str] = None, drug_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve community reports by batch or drug GSI."""
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_REPORTS_TABLE)

    if batch_no:
        res = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(f"BATCH#{batch_no}"),
            Limit=50,
        )
        reports = [convert_decimals_to_primitives(i) for i in res.get("Items", [])]
    elif drug_name:
        res = table.query(
            IndexName="GSI2",
            KeyConditionExpression=Key("GSI2PK").eq(f"DRUG#{drug_name.lower().strip()}"),
            Limit=50,
        )
        reports = [convert_decimals_to_primitives(i) for i in res.get("Items", [])]
    else:
        return {"report_count": 0, "reports": [], "community_flag": False}

    return {
        "report_count": len(reports),
        "reports": reports,
        "community_flag": any(report.get("status") == "APPROVED" for report in reports),
    }


@tool
def search_drug(fuzzy_text: str, size: int = 5) -> Dict[str, Any]:
    """Find likely drug, manufacturer, and batch matches."""
    query = {
        "size": size,
        "query": {
            "fuzzy": {
                "search_text": {
                    "value": fuzzy_text,
                    "fuzziness": "AUTO",
                    "prefix_length": 1,
                }
            }
        },
    }
    hits = opensearch_search(settings.OPENSEARCH_INDEX_DRUGS, query)
    return {
        "candidates": [
            {
                "drug_name": hit.get("_source", {}).get("drug_name"),
                "manufacturer": hit.get("_source", {}).get("manufacturer_name"),
                "batch_no": hit.get("_source", {}).get("batch_no"),
                "score": hit.get("_score", 0.0),
            }
            for hit in hits
        ]
    }


SKILL_TOOLS = [check_batch, get_manufacturer_history, get_notice, get_case_history, get_community_reports, search_drug]