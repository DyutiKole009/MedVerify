"""
DynamoDB Streams aggregation handler for manufacturer metrics (§4.4).
Recomputes total NSQ and spurious batch counts idempotently upon batch alert insertions.
"""
from typing import Dict, Any, List
from boto3.dynamodb.conditions import Key

from src.tools.aws import get_dynamodb_resource, convert_floats_to_decimals
from src.config import settings
from src.utils.logger import logger


def recompute_manufacturer_metrics(manufacturer_id: str) -> Dict[str, Any]:
    """
    Derives total NSQ, Spurious, and community flag counts for a manufacturer via Batches GSI2.
    Idempotent recompute ensures correctness even under at-least-once stream deliveries.
    """
    dynamo = get_dynamodb_resource()
    batches_table = dynamo.Table(settings.DYNAMODB_BATCHES_TABLE)
    mfr_table = dynamo.Table(settings.DYNAMODB_MANUFACTURERS_TABLE)

    pk_val = f"MFR#{manufacturer_id}"
    res = batches_table.query(
        IndexName="GSI2",
        KeyConditionExpression=Key("GSI2PK").eq(pk_val) & Key("GSI2SK").begins_with("BATCH#"),
    )
    items = res.get("Items", [])

    total_nsq = sum(1 for i in items if i.get("alert_status") == "NSQ")
    total_spurious = sum(1 for i in items if i.get("alert_status") == "SPURIOUS")
    total_flagged = sum(1 for i in items if i.get("community_flag"))

    latest_date = None
    canonical_name = manufacturer_id.replace("_", " ").title()

    for item in items:
        mfr_name = item.get("manufacturer_name")
        if mfr_name:
            canonical_name = mfr_name
        dt = item.get("source_month") or item.get("ingested_at")
        if dt and (not latest_date or dt > latest_date):
            latest_date = dt

    update_payload = {
        "PK": pk_val,
        "canonical_name": canonical_name,
        "total_nsq_batches": total_nsq,
        "total_spurious_batches": total_spurious,
        "total_community_flagged_batches": total_flagged,
        "last_incident_date": latest_date,
    }

    mfr_table.put_item(Item=convert_floats_to_decimals(update_payload))
    logger.info(f"Recomputed metrics for {pk_val}: NSQ={total_nsq}, Spurious={total_spurious}")
    return update_payload


def handle_batch_stream_event(event: Dict[str, Any]) -> int:
    """
    Entry point for DynamoDB Stream Lambda invocations.
    Processes Records from Batches table stream.
    """
    records: List[Dict[str, Any]] = event.get("Records", [])
    mfr_ids_to_recompute = set()

    for rec in records:
        event_name = rec.get("eventName")
        if event_name not in ("INSERT", "MODIFY"):
            continue

        dynamodb_data = rec.get("dynamodb", {})
        new_image = dynamodb_data.get("NewImage", {})

        # Extract normalized manufacturer ID
        mfr_id_attr = new_image.get("manufacturer_id_normalized", {})
        mfr_id = mfr_id_attr.get("S")
        if mfr_id:
            mfr_ids_to_recompute.add(mfr_id)

    for mfr_id in mfr_ids_to_recompute:
        recompute_manufacturer_metrics(mfr_id)

    return len(mfr_ids_to_recompute)
