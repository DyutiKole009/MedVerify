import pytest
from unittest.mock import MagicMock, patch
from src.aws_wrappers.cognito import CognitoWrapper

@pytest.fixture
def mock_cognito_client():
    with patch("src.aws_wrappers.cognito.get_boto_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client

def test_admin_get_user(mock_cognito_client):
    mock_cognito_client.admin_get_user.return_value = {
        "Username": "pharmacist_john",
        "UserStatus": "CONFIRMED",
        "Enabled": True,
        "UserAttributes": [
            {"Name": "email", "Value": "john@pharmacy.com"},
            {"Name": "custom:role", "Value": "consumer"}
        ]
    }
    wrapper = CognitoWrapper()
    user = wrapper.admin_get_user("pharmacist_john", user_pool_id="mock_pool_id")

    assert user["username"] == "pharmacist_john"
    assert user["status"] == "CONFIRMED"
    assert user["enabled"] is True
    assert user["attributes"]["custom:role"] == "consumer"
    mock_cognito_client.admin_get_user.assert_called_once_with(
        UserPoolId="mock_pool_id",
        Username="pharmacist_john"
    )

def test_admin_update_user_role(mock_cognito_client):
    wrapper = CognitoWrapper()
    result = wrapper.admin_update_user_role("pharmacist_john", "pharmacist", user_pool_id="mock_pool_id")
    assert result is True
    mock_cognito_client.admin_update_user_attributes.assert_called_once_with(
        UserPoolId="mock_pool_id",
        Username="pharmacist_john",
        UserAttributes=[{"Name": "custom:role", "Value": "pharmacist"}]
    )

def test_admin_add_user_to_group(mock_cognito_client):
    wrapper = CognitoWrapper()
    result = wrapper.admin_add_user_to_group("pharmacist_john", "pharmacist", user_pool_id="mock_pool_id")
    assert result is True
    mock_cognito_client.admin_add_user_to_group.assert_called_once_with(
        UserPoolId="mock_pool_id",
        Username="pharmacist_john",
        GroupName="pharmacist"
    )
