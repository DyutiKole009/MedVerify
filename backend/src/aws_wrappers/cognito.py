"""
Amazon Cognito wrapper for user management, role elevation, and identity verification.
"""
from typing import Dict, Any, Optional, List
from src.aws_wrappers.base import BaseAWSWrapper, catch_aws_errors
from src.aws_wrappers.client_factory import get_boto_client
from src.config import settings
from src.utils.logger import logger

class CognitoWrapper(BaseAWSWrapper):
    """Encapsulates Amazon Cognito User Pool administrative actions (§8)."""
    def __init__(self):
        super().__init__("CognitoIDP")
        self.client = get_boto_client("cognito-idp")

    @catch_aws_errors("AdminGetUser")
    def admin_get_user(
        self,
        username: str,
        user_pool_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetches user details and attributes from Cognito."""
        pool_id = user_pool_id or settings.COGNITO_USER_POOL_ID
        response = self.client.admin_get_user(
            UserPoolId=pool_id,
            Username=username
        )
        attributes = {attr["Name"]: attr["Value"] for attr in response.get("UserAttributes", [])}
        return {
            "username": response.get("Username"),
            "status": response.get("UserStatus"),
            "enabled": response.get("Enabled"),
            "attributes": attributes
        }

    @catch_aws_errors("AdminUpdateUserRole")
    def admin_update_user_role(
        self,
        username: str,
        role: str,
        user_pool_id: Optional[str] = None
    ) -> bool:
        """
        Updates the custom:role attribute for a user (e.g. consumer -> pharmacist/admin) (§8).
        """
        pool_id = user_pool_id or settings.COGNITO_USER_POOL_ID
        self.client.admin_update_user_attributes(
            UserPoolId=pool_id,
            Username=username,
            UserAttributes=[
                {
                    "Name": "custom:role",
                    "Value": role
                }
            ]
        )
        logger.info(f"Updated role for user {username} to {role}")
        return True

    @catch_aws_errors("AdminAddUserToGroup")
    def admin_add_user_to_group(
        self,
        username: str,
        group_name: str,
        user_pool_id: Optional[str] = None
    ) -> bool:
        """Adds a user to a Cognito group (e.g. admin or pharmacist)."""
        pool_id = user_pool_id or settings.COGNITO_USER_POOL_ID
        self.client.admin_add_user_to_group(
            UserPoolId=pool_id,
            Username=username,
            GroupName=group_name
        )
        return True
