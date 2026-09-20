"""
Authentication and authorization dependencies for FastAPI endpoints (§8).
Supports Amazon Cognito JWT authentication and client-side anonymous ID tracking.
"""
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status

from src.tools.cognito import verify_cognito_jwt
from src.utils.logger import logger


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
            user_data = verify_cognito_jwt(token)
            # If name or email missing, fetch from Cognito via get_user_attributes_from_token
            if not user_data.get("name") or not user_data.get("email"):
                from src.tools.cognito import get_user_attributes_from_token, get_user_profile_by_sub
                extra = get_user_attributes_from_token(token)
                if not extra and user_data.get("user_id"):
                    extra = get_user_profile_by_sub(user_data["user_id"])
                if extra:
                    if not user_data.get("name") and extra.get("name"):
                        user_data["name"] = extra.get("name")
                    if not user_data.get("email") and extra.get("email"):
                        user_data["email"] = extra.get("email")
                    if extra.get("role"):
                        user_data["role"] = extra.get("role")

            return {
                "user_id": user_data["user_id"],
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "role": user_data.get("role", "consumer"),
                "groups": user_data.get("groups", []),
                "is_authenticated": True,
            }
        except Exception as exc:
            logger.warning(f"Cognito token validation failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired authorization token: {exc}",
            )

    # Anonymous user fallback (§7)
    anon_id = x_anonymous_id or "anon_guest"
    return {
        "user_id": anon_id,
        "email": None,
        "role": "consumer",
        "groups": [],
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
            detail="Authentication required for this operation. Provide a valid Bearer token.",
        )
    return user


def require_admin_user(
    authorization: Optional[str] = Header(None),
    x_anonymous_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Requires an authenticated user belonging to the admin role (§8)."""
    user = require_authenticated_user(authorization, x_anonymous_id)
    if user["role"] != "admin" and "admin" not in user.get("groups", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this action",
        )
    return user
