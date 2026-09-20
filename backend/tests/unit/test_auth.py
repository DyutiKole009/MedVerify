import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import jwt

from src.main import app

client = TestClient(app)


@patch("src.tools.cognito.get_cognito_client")
def test_signup_success(mock_get_cognito):
    mock_cognito = MagicMock()
    mock_get_cognito.return_value = mock_cognito
    mock_cognito.sign_up.return_value = {
        "UserSub": "user-uuid-1234",
        "UserConfirmed": False,
    }

    res = client.post(
        "/auth/signup",
        json={
            "email": "pharmacist@medverify.io",
            "password": "SecurePassword123!",
            "role": "pharmacist",
            "name": "Dr. Sarah Rao",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "CONFIRMATION_PENDING"
    assert data["user_id"] == "user-uuid-1234"
    assert data["email"] == "pharmacist@medverify.io"


def test_signup_invalid_role():
    res = client.post(
        "/auth/signup",
        json={
            "email": "test@medverify.io",
            "password": "SecurePassword123!",
            "role": "invalid_role",
        },
    )
    assert res.status_code == 400


@patch("src.tools.cognito.get_cognito_client")
def test_confirm_signup(mock_get_cognito):
    mock_cognito = MagicMock()
    mock_get_cognito.return_value = mock_cognito
    mock_cognito.confirm_sign_up.return_value = {}

    res = client.post(
        "/auth/confirm",
        json={
            "email": "pharmacist@medverify.io",
            "confirmation_code": "123456",
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "CONFIRMED"


@patch("src.tools.cognito.get_cognito_client")
def test_login_success(mock_get_cognito):
    mock_cognito = MagicMock()
    mock_get_cognito.return_value = mock_cognito

    # Mock id token with claims
    id_token = jwt.encode(
        {"sub": "user-uuid-1234", "email": "user@medverify.io", "custom:role": "consumer"},
        "secret",
        algorithm="HS256",
    )
    mock_cognito.initiate_auth.return_value = {
        "AuthenticationResult": {
            "AccessToken": "access-token-xyz",
            "IdToken": id_token,
            "RefreshToken": "refresh-token-xyz",
            "ExpiresIn": 3600,
            "TokenType": "Bearer",
        }
    }

    res = client.post(
        "/auth/login",
        json={
            "email": "user@medverify.io",
            "password": "ValidPassword123!",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["access_token"] == "access-token-xyz"
    assert data["token_type"] == "Bearer"
    assert data["role"] == "consumer"
    assert data["user_id"] == "user-uuid-1234"


@patch("src.tools.cognito.get_cognito_client")
def test_refresh_token(mock_get_cognito):
    mock_cognito = MagicMock()
    mock_get_cognito.return_value = mock_cognito
    mock_cognito.initiate_auth.return_value = {
        "AuthenticationResult": {
            "AccessToken": "new-access-token-123",
            "IdToken": "new-id-token-123",
            "ExpiresIn": 3600,
            "TokenType": "Bearer",
        }
    }

    res = client.post("/auth/refresh", json={"refresh_token": "valid-refresh-token"})
    assert res.status_code == 200
    assert res.json()["access_token"] == "new-access-token-123"


@patch("src.tools.cognito.get_cognito_client")
def test_resend_code(mock_get_cognito):
    mock_cognito = MagicMock()
    mock_get_cognito.return_value = mock_cognito
    mock_cognito.resend_confirmation_code.return_value = {
        "CodeDeliveryDetails": {"Destination": "u***@medverify.io", "DeliveryMedium": "EMAIL"}
    }

    res = client.post("/auth/resend-code", json={"email": "user@medverify.io"})
    assert res.status_code == 200
    assert res.json()["status"] == "SENT"


@patch("src.tools.cognito.get_cognito_client")
def test_forgot_and_reset_password(mock_get_cognito):
    mock_cognito = MagicMock()
    mock_get_cognito.return_value = mock_cognito
    mock_cognito.forgot_password.return_value = {
        "CodeDeliveryDetails": {"Destination": "u***@medverify.io"}
    }
    mock_cognito.confirm_forgot_password.return_value = {}

    forgot_res = client.post("/auth/forgot-password", json={"email": "user@medverify.io"})
    assert forgot_res.status_code == 200
    assert forgot_res.json()["status"] == "RESET_CODE_SENT"

    reset_res = client.post(
        "/auth/reset-password",
        json={
            "email": "user@medverify.io",
            "confirmation_code": "654321",
            "new_password": "BrandNewPassword123!",
        },
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "SUCCESS"


def test_get_me_authorized():
    token = jwt.encode(
        {"sub": "user_456", "email": "pharmacist@medverify.io", "custom:role": "pharmacist"},
        "secret",
        algorithm="HS256",
    )
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "user_456"
    assert data["email"] == "pharmacist@medverify.io"
    assert data["role"] == "pharmacist"


def test_get_me_unauthorized():
    res = client.get("/auth/me")
    assert res.status_code == 401
