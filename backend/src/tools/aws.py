"""
AWS client helpers and utility functions loaded directly from environment settings.
"""
from typing import Any, Dict, List, Optional
from decimal import Decimal
import json
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

from src.config import settings


def get_boto_session() -> boto3.Session:
    """Initializes a boto3 Session from environment settings."""
    kwargs = {"region_name": settings.AWS_REGION}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        if settings.AWS_SESSION_TOKEN:
            kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN
    return boto3.Session(**kwargs)


def get_dynamodb_resource():
    """Returns DynamoDB resource configured from env."""
    return get_boto_session().resource("dynamodb")


def get_s3_client():
    """Returns S3 client configured from env."""
    return get_boto_session().client("s3")


def get_bedrock_runtime_client():
    """Returns Bedrock Runtime client configured from env."""
    return get_boto_session().client("bedrock-runtime")


def get_bedrock_agent_runtime_client():
    """Returns Bedrock Agent Runtime client for Knowledge Bases from env."""
    return get_boto_session().client("bedrock-agent-runtime")


def get_agentcore_client():
    """Returns Bedrock AgentCore Memory client from env."""
    return get_boto_session().client("bedrock-agentcore")


def convert_floats_to_decimals(obj: Any) -> Any:
    """Recursively converts floats to Decimals for DynamoDB serialization."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimals(v) for v in obj]
    return obj


def convert_decimals_to_primitives(obj: Any) -> Any:
    """Recursively converts Decimals from DynamoDB into python primitives."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: convert_decimals_to_primitives(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_decimals_to_primitives(v) for v in obj]
    return obj


def opensearch_search(index_name: str, query: Dict[str, Any], endpoint: Optional[str] = None) -> List[Dict[str, Any]]:
    """Executes a search query against OpenSearch Serverless with SigV4 signing."""
    ep = (endpoint or settings.OPENSEARCH_ENDPOINT).rstrip("/")
    url = f"{ep}/{index_name.lstrip('/')}/_search"
    session = get_boto_session()
    credentials = session.get_credentials()
    data = json.dumps(query)
    headers = {"Content-Type": "application/json"}

    if credentials:
        frozen_creds = credentials.get_frozen_credentials()
        if frozen_creds:
            request = AWSRequest(method="POST", url=url, data=data, headers=headers)
            SigV4Auth(frozen_creds, "aoss", settings.AWS_REGION).add_auth(request)
            headers = dict(request.headers)

    response = requests.post(url, data=data, headers=headers, timeout=10)
    if not response.ok:
        return []
    hits = response.json().get("hits", {}).get("hits", [])
    return hits
