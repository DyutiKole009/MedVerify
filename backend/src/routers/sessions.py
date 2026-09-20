"""
Sessions & Feedback API router (§12.1 GET /sessions/{id} & POST /sessions/{id}/feedback).
Also provides user session history (§8 GET /users/{user_id}/sessions).
"""
from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from boto3.dynamodb.conditions import Key, Attr

from src.models.schemas import FeedbackRequest
from src.tools.aws import get_dynamodb_resource, convert_decimals_to_primitives
from src.dependencies.auth import get_current_user_optional, require_authenticated_user
from src.config import settings

router = APIRouter()


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
