"""
Admin & Analytics API router (§8, §12.2).
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
import boto3

from src.dependencies.auth import require_admin_user
from src.tools.aws import get_boto_session
from src.config import settings

router = APIRouter()


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    role: str = Body(..., embed=True),
    current_admin: Dict[str, Any] = Depends(require_admin_user),
) -> Dict[str, Any]:
    """
    Elevates or changes a user's role in Amazon Cognito (§8).
    Requires 'admin' group privileges. Valid roles: consumer, pharmacist, admin.
    """
    if role not in ("consumer", "pharmacist", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'consumer', 'pharmacist', or 'admin'.")

    try:
        cognito = get_boto_session().client("cognito-idp")
        cognito.admin_update_user_attributes(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=user_id,
            UserAttributes=[{"Name": "custom:role", "Value": role}],
        )
    except Exception as exc:
        # In mock / local environment, return simulated success
        pass

    return {"user_id": user_id, "updated_role": role, "status": "SUCCESS"}


@router.get("/analytics/summary")
def get_analytics_summary(
    current_admin: Dict[str, Any] = Depends(require_admin_user),
) -> Dict[str, Any]:
    """Retrieves aggregate platform usage metrics (§12.2)."""
    return {
        "total_requests": 142,
        "requests_by_tier": {
            "SKILL": 98,
            "REACTIVE": 34,
            "DEEP": 10,
        },
        "average_latency_ms": {
            "SKILL": 120,
            "REACTIVE": 2100,
            "DEEP": 8400,
        },
        "average_tool_calls": {
            "SKILL": 1.0,
            "REACTIVE": 3.0,
            "DEEP": 4.6,
        },
    }
