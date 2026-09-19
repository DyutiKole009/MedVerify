"""
Skill Agent — deterministic one-shot lookup.

Tool sequence (fixed, no model backbone required):
  1. check_batch          — CDSCO batch record + NSQ/spurious status
  2. get_community_reports — crowd-sourced reports for this batch/drug
  3. get_manufacturer_history — manufacturer risk profile
"""
import uuid
from typing import Any, Dict, Optional

from src.tools.skill_tools import check_batch, get_community_reports, get_manufacturer_history
from src.tools.aws import get_dynamodb_resource, convert_floats_to_decimals
from src.config import settings


def run_skill_agent(
    batch_no: Optional[str] = None,
    drug_name: Optional[str] = None,
    manufacturer_name: Optional[str] = "",
    session_id: Optional[str] = None,
    **_kwargs,
) -> Dict[str, Any]:
    """
    Run the Skill Agent tool sequence and return a consolidated result.
    No model required — tool order is fixed for batch/text lookups.
    """
    session_id = session_id or str(uuid.uuid4())

    # Tool 1: batch record + NSQ/spurious flag
    batch_result = check_batch(
        batch_no=batch_no or "",
        drug_name=drug_name,
        manufacturer=manufacturer_name,
    )

    # Tool 2: community crowd reports
    community_result = get_community_reports(
        batch_no=batch_no,
        drug_name=drug_name,
    )

    # Tool 3: manufacturer history
    mfg_result = get_manufacturer_history(manufacturer_name or "")

    batch_record   = batch_result.get("batch_record")
    community_flag = community_result.get("community_flag", False)

    if not batch_result.get("found"):
        status_category = "NO_MATCH"
    elif batch_record and batch_record.get("alert_status") == "SPURIOUS":
        status_category = "SPURIOUS"
    elif batch_record and batch_record.get("alert_status") == "NSQ":
        status_category = "NSQ"
    elif community_flag:
        status_category = "COMMUNITY_FLAGGED"
    elif batch_record and batch_record.get("alert_status"):
        status_category = batch_record.get("alert_status")
    else:
        status_category = "MATCH_FOUND"

    result = {
        "session_id":           session_id,
        "tier":                 "SKILL",
        "status_category":      status_category,
        "batch_record":         batch_record,
        "community_flag":       community_flag,
        "community_reports":    community_result.get("reports", []),
        "manufacturer_history": mfg_result,
        "limitation_statement": "Absence of a flag is not proof of safety.",
    }

    # Persist to DynamoDB
    dynamo = get_dynamodb_resource()
    table  = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
    table.update_item(
        Key={"PK": f"SESSION#{session_id}", "SK": "META"},
        UpdateExpression="SET final_result = :r, #st = :s",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":r": convert_floats_to_decimals(result),
            ":s": "DONE",
        },
    )

    return result