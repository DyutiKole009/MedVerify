"""
MedVerify FastAPI Server Application and AWS Lambda Handler (§12).
"""
from typing import Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from boto3.dynamodb.conditions import Attr

try:
    from mangum import Mangum
except ImportError:
    Mangum = None

from src.routers import (
    check_router,
    investigate_router,
    sessions_router,
    reports_router,
    uploads_router,
    batches_router,
    admin_router,
    auth_router,
)
from src.tools.aws import get_dynamodb_resource, convert_decimals_to_primitives
from src.dependencies.auth import require_authenticated_user
from src.config import settings
from src.utils.logger import logger

app = FastAPI(
    title="MedVerify API",
    description="Regulatory verification, AI counterfeit investigation, and community safety reporting for medicines.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth_router, prefix="/auth", tags=["Cognito Authentication"])
app.include_router(check_router, prefix="/check", tags=["Quick Check"])
app.include_router(investigate_router, prefix="/investigate", tags=["Investigation"])
app.include_router(sessions_router, prefix="/sessions", tags=["Sessions & Feedback"])
app.include_router(reports_router, prefix="/reports", tags=["Community Reports"])
app.include_router(uploads_router, prefix="/uploads", tags=["Uploads"])
app.include_router(batches_router, tags=["Batches & Manufacturers"])
app.include_router(admin_router, prefix="/admin", tags=["Admin & Analytics"])


@app.get("/users/{user_id}/sessions", tags=["User History"])
def get_user_session_history(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
) -> Dict[str, Any]:
    """
    Retrieves previous medicine verification sessions for a user (§8).
    Users can inspect their own history, or admins can view any user's history.
    """
    if current_user["user_id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="You do not have access to this user's history.")

    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)

    try:
        resp = table.scan(
            FilterExpression=Attr("user_id").eq(user_id),
            Limit=50,
        )
        sessions = [convert_decimals_to_primitives(item) for item in resp.get("Items", [])]
        return {
            "user_id": user_id,
            "count": len(sessions),
            "sessions": sessions,
        }
    except Exception as exc:
        logger.warning(f"Failed to scan user sessions: {exc}")
        return {"user_id": user_id, "count": 0, "sessions": []}


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for container and API Gateway monitoring."""
    return {
        "status": "healthy",
        "service": "MedVerify Backend",
        "version": "2.0.0",
        "region": settings.AWS_REGION,
    }


# Mangum adapter for AWS Lambda / API Gateway serverless deployment
handler = Mangum(app) if Mangum else None
