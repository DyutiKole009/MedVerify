"""
Amazon Cognito Authentication & Identity API router (§8).
Provides endpoints for signup, verification, login, token refresh, and profile inspection.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from botocore.exceptions import ClientError

from src.models.schemas import (
    SignUpRequest,
    ConfirmSignUpRequest,
    LoginRequest,
    RefreshTokenRequest,
    ResendCodeRequest,
    ForgotPasswordRequest,
    ConfirmForgotPasswordRequest,
    TokenResponse,
    UserProfileResponse,
)
from src.tools import cognito
from src.dependencies.auth import require_authenticated_user
from src.utils.logger import logger

router = APIRouter()


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def register_user(request: SignUpRequest) -> Dict[str, Any]:
    """
    Registers a new user in the Amazon Cognito User Pool (§8).
    Supports roles: consumer, pharmacist.
    """
    if request.role not in ("consumer", "pharmacist"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'consumer' or 'pharmacist'.",
        )

    try:
        res = cognito.sign_up(
            email=request.email,
            password=request.password,
            role=request.role or "consumer",
            name=request.name,
        )
        return {
            "status": res["status"],
            "user_id": res["user_sub"],
            "email": request.email,
            "message": "User registered successfully. Check your email for verification code.",
        }
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "SignUpError")
        msg = exc.response.get("Error", {}).get("Message", str(exc))
        if code == "UsernameExistsException":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as exc:
        logger.error(f"Unexpected signup error: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed.")


@router.post("/confirm")
def confirm_user_email(request: ConfirmSignUpRequest) -> Dict[str, Any]:
    """
    Verifies the user's email address using the confirmation code sent by Cognito (§8).
    """
    try:
        res = cognito.confirm_sign_up(
            email=request.email,
            confirmation_code=request.confirmation_code,
        )
        return {"status": "CONFIRMED", "message": "Email verified successfully. You can now log in."}
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "ConfirmError")
        msg = exc.response.get("Error", {}).get("Message", str(exc))
        if code == "CodeMismatchException":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code.")
        if code == "ExpiredCodeException":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code has expired. Request a new one.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post("/login", response_model=TokenResponse)
def login_user(request: LoginRequest) -> TokenResponse:
    """
    Authenticates user with Amazon Cognito via USER_PASSWORD_AUTH (§8).
    Returns JWT access_token, id_token, and refresh_token.
    """
    try:
        tokens = cognito.initiate_auth(
            email=request.email,
            password=request.password,
        )
        # Inspect claims from access or ID token
        token_for_claims = tokens.get("id_token") or tokens.get("access_token")
        user_info = cognito.verify_cognito_jwt(token_for_claims) if token_for_claims else {}

        name = user_info.get("name")
        email = user_info.get("email") or request.email
        role = user_info.get("role", "consumer")
        user_id = user_info.get("user_id")

        if not name and tokens.get("access_token"):
            extra = cognito.get_user_attributes_from_token(tokens["access_token"])
            name = extra.get("name")
            if extra.get("email"):
                email = extra.get("email")
            if extra.get("role"):
                role = extra.get("role")

        if not name and user_id:
            extra = cognito.get_user_profile_by_sub(user_id)
            name = extra.get("name") or name
            if extra.get("email"):
                email = extra.get("email")

        if not name and email:
            extra = cognito.get_user_profile_by_sub(email)
            name = extra.get("name") or name

        return TokenResponse(
            access_token=tokens["access_token"],
            id_token=tokens.get("id_token"),
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens.get("expires_in", 3600),
            token_type=tokens.get("token_type", "Bearer"),
            role=role,
            user_id=user_id,
            email=email,
            name=name,
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "AuthError")
        msg = exc.response.get("Error", {}).get("Message", str(exc))
        if code in ("NotAuthorizedException", "UserNotFoundException"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
        if code == "UserNotConfirmedException":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User email is not verified. Please verify your email first.",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post("/refresh", response_model=TokenResponse)
def refresh_user_token(request: RefreshTokenRequest) -> TokenResponse:
    """Refreshes Cognito access and ID tokens using a refresh token."""
    try:
        tokens = cognito.refresh_token(request.refresh_token)
        return TokenResponse(
            access_token=tokens["access_token"],
            id_token=tokens.get("id_token"),
            refresh_token=request.refresh_token,
            expires_in=tokens.get("expires_in", 3600),
            token_type=tokens.get("token_type", "Bearer"),
        )
    except ClientError as exc:
        msg = exc.response.get("Error", {}).get("Message", "Could not refresh token.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)


@router.post("/resend-code")
def resend_code(request: ResendCodeRequest) -> Dict[str, Any]:
    """Resends email confirmation code to the user."""
    try:
        res = cognito.resend_confirmation_code(request.email)
        return {
            "status": "SENT",
            "message": f"Verification code resent to {res.get('destination', request.email)}.",
        }
    except ClientError as exc:
        msg = exc.response.get("Error", {}).get("Message", str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post("/forgot-password")
def trigger_forgot_password(request: ForgotPasswordRequest) -> Dict[str, Any]:
    """Sends a password reset code to the registered email."""
    try:
        res = cognito.forgot_password(request.email)
        return {
            "status": "RESET_CODE_SENT",
            "message": f"Password reset code sent to {res.get('destination', request.email)}.",
        }
    except ClientError as exc:
        msg = exc.response.get("Error", {}).get("Message", str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post("/reset-password")
def reset_password(request: ConfirmForgotPasswordRequest) -> Dict[str, Any]:
    """Resets password using the verification code received via email."""
    try:
        cognito.confirm_forgot_password(
            email=request.email,
            confirmation_code=request.confirmation_code,
            new_password=request.new_password,
        )
        return {"status": "SUCCESS", "message": "Password reset successfully. You can now log in."}
    except ClientError as exc:
        msg = exc.response.get("Error", {}).get("Message", str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
) -> UserProfileResponse:
    """
    Returns profile information and assigned role for the authenticated user (§8).
    Requires a valid Cognito JWT in the Authorization header.
    """
    return UserProfileResponse(
        user_id=current_user["user_id"],
        email=current_user.get("email"),
        role=current_user.get("role", "consumer"),
        name=current_user.get("name"),
        email_verified=True,
    )
