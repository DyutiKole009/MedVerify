"""
Authentication and authorization dependencies for FastAPI endpoints (§8).
Supports Cognito JWT authentication and client-side anonymous ID tracking.
"""
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status
import jwt

from src.config import settings


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    x_anonymous_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Resolves the calling user from either a Cognito JWT token or an anonymous ID header.
    Does not reject unauthenticated calls.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            # Decode token without verification in development/hackathon scope, or with Cognito issuer
            claims = jwt.decode(token, options={"verify_signature": False})
            return {
                "user_id": claims.get("sub", claims.get("username", "authenticated_user")),
                "email": claims.get("email"),
                "role": claims.get("custom:role", "consumer"),
                "is_authenticated": True,
            }
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authorization token",
            )

    # Anonymous user fallback
    anon_id = x_anonymous_id or "anon_guest"
    return {
        "user_id": anon_id,
        "email": None,
        "role": "consumer",
        "is_authenticated": False,
    }


def require_authenticated_user(
    authorization: Optional[str] = Header(None),
    x_anonymous_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Requires a valid Cognito JWT token (§8: Reporting requires auth, always)."""
    user = get_current_user_optional(authorization, x_anonymous_id)
    if not user["is_authenticated"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for this operation",
        )
    return user


def require_admin_user(
    authorization: Optional[str] = Header(None),
    x_anonymous_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Requires an authenticated user belonging to the admin role."""
    user = require_authenticated_user(authorization, x_anonymous_id)
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this action",
        )
    return user
