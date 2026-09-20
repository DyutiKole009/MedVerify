"""
Sessions & Feedback API router (§12.1 GET /sessions, GET /sessions/{id}, POST /sessions, POST /sessions/{id}/feedback).
Also provides user session history (§8 GET /users/{user_id}/sessions).
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from boto3.dynamodb.conditions import Key, Attr
from pydantic import BaseModel, Field

from src.models.schemas import FeedbackRequest
from src.tools.aws import get_dynamodb_resource, convert_decimals_to_primitives, convert_floats_to_decimals
from src.dependencies.auth import get_current_user_optional, require_authenticated_user
from src.config import settings
from src.utils.logger import logger

router = APIRouter()


class SaveSessionRequest(BaseModel):
    id: Optional[str] = None
    drugName: Optional[str] = None
    batchNo: Optional[str] = None
    status: Optional[str] = "CLEAR"
    query: Optional[str] = None
    summary: Optional[str] = None
    imageUrl: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    messages: Optional[List[Dict[str, Any]]] = None
    timestamp: Optional[str] = None


@router.get("")
def list_user_sessions(
    user: Dict[str, Any] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """
    Retrieves all past medicine verification sessions for the current user or guest (§8).
    Enables chat history to persist across logout and login.
    """
    user_id = user["user_id"]
    email = user.get("email")

    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)

    try:
        if email and email != user_id:
            filter_exp = Attr("user_id").eq(user_id) | Attr("user_id").eq(email)
        else:
            filter_exp = Attr("user_id").eq(user_id)

        resp = table.scan(
            FilterExpression=filter_exp,
            Limit=50,
        )

        items = [convert_decimals_to_primitives(it) for it in resp.get("Items", [])]

        formatted_sessions = []
        for it in items:
            s_id = it.get("PK", "").replace("SESSION#", "")
            input_data = it.get("input_data", {})
            batch_record = it.get("batch_record") or {}
            final_result = it.get("final_result") or it.get("result") or {}

            drug_name = (
                it.get("drug_name")
                or input_data.get("drug_name")
                or batch_record.get("drug_name")
                or (it.get("extracted_fields") or {}).get("drug_name")
                or "Medicine Verification"
            )

            batch_no = (
                it.get("batch_no")
                or input_data.get("batch_no")
                or batch_record.get("batch_no")
                or (it.get("extracted_fields") or {}).get("batch_no")
                or "N/A"
            )

            status_val = (
                it.get("status_category")
                or final_result.get("status_category")
                or batch_record.get("alert_status")
                or ("SPURIOUS" if it.get("spurious") else "CLEAR")
            )

            created_time = it.get("created_at") or it.get("completed_at") or it.get("timestamp") or datetime.now(timezone.utc).isoformat()

            formatted_sessions.append({
                "id": s_id,
                "timestamp": created_time,
                "drugName": drug_name,
                "batchNo": batch_no,
                "status": status_val,
                "query": it.get("query") or f"Verify {drug_name} ({batch_no})",
                "summary": it.get("summary") or final_result.get("summary"),
                "result": final_result or {
                    "session_id": s_id,
                    "status_category": status_val,
                    "batch_record": batch_record or None,
                    "summary": it.get("summary"),
                    "community_flag": it.get("community_flag", False),
                    "disclaimer": "Absence of a flag is not proof of safety.",
                },
                "messages": it.get("messages", []),
                "imageUrl": it.get("imageUrl") or input_data.get("image_s3_key"),
            })

        # Sort descending by timestamp
        formatted_sessions.sort(key=lambda s: s["timestamp"], reverse=True)

        return {
            "user_id": user_id,
            "count": len(formatted_sessions),
            "sessions": formatted_sessions,
        }
    except Exception as exc:
        logger.warning(f"Failed to scan user sessions: {exc}")
        return {"user_id": user_id, "count": 0, "sessions": []}


@router.post("")
def save_user_session(
    payload: SaveSessionRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """
    Saves or updates a verification session with its full chat history in DynamoDB (§8, §12.1).
    """
    session_id = payload.id or str(uuid.uuid4())
    now_iso = payload.timestamp or datetime.now(timezone.utc).isoformat()

    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)

    item: Dict[str, Any] = {
        "PK": f"SESSION#{session_id}",
        "SK": "META",
        "user_id": user["user_id"],
        "drug_name": payload.drugName,
        "batch_no": payload.batchNo,
        "status_category": payload.status,
        "status": "DONE",
        "query": payload.query,
        "summary": payload.summary,
        "imageUrl": payload.imageUrl,
        "result": payload.result,
        "messages": payload.messages or [],
        "created_at": now_iso,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    table.put_item(Item=convert_floats_to_decimals(item))
    return {"status": "SAVED", "session_id": session_id}


@router.get("/{session_id}")
def get_session(
    session_id: str,
    user: Dict[str, Any] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """Retrieves session details and results for polling or review (§12.1)."""
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)

    response = table.get_item(Key={"PK": f"SESSION#{session_id}", "SK": "META"})
    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return convert_decimals_to_primitives(item)


@router.delete("/{session_id}")
def delete_session(
    session_id: str,
    user: Dict[str, Any] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """Deletes a session record from DynamoDB."""
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
    table.delete_item(Key={"PK": f"SESSION#{session_id}", "SK": "META"})
    return {"deleted": True, "session_id": session_id}


@router.post("/{session_id}/feedback")
def submit_feedback(
    session_id: str,
    feedback: FeedbackRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """
    Records user feedback (helpful/not helpful) on an investigation result (§7, §12.1).
    Feeds the RAG feedback promotion gate.
    """
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)

    # Check session exists
    response = table.get_item(Key={"PK": f"SESSION#{session_id}", "SK": "META"})
    if not response.get("Item"):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    feedback_data = {
        "helpful": feedback.helpful,
        "comment": feedback.comment or "",
        "submitted_at": now_iso,
        "user_id": user["user_id"],
    }

    table.update_item(
        Key={"PK": f"SESSION#{session_id}", "SK": "META"},
        UpdateExpression="SET feedback = :f",
        ExpressionAttributeValues={":f": feedback_data},
    )

    return {"recorded": True}

