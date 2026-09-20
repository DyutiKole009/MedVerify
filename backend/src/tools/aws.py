"""
AWS service client factories, credentials management, and utility helpers.
DynamoDB, S3, Textract, Rekognition, OpenSearch Serverless, and Gemini client.
"""
import json
from decimal import Decimal
from typing import Any, Dict, List, Optional
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

from src.config import settings
from src.utils.logger import logger

_BOTO_SESSION: Optional[boto3.Session] = None


def get_boto_session() -> boto3.Session:
    """Returns cached boto3 Session configured with environment region and credentials."""
    global _BOTO_SESSION
    if _BOTO_SESSION is None:
        _BOTO_SESSION = boto3.Session(
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
            aws_session_token=settings.AWS_SESSION_TOKEN or None,
        )
    return _BOTO_SESSION


def get_dynamodb_resource():
    """Returns DynamoDB resource configured from env."""
    return get_boto_session().resource("dynamodb")


def get_s3_client():
    """Returns S3 client configured from env."""
    return get_boto_session().client("s3")


def get_rekognition_client():
    """Returns Amazon Rekognition client configured from env."""
    return get_boto_session().client("rekognition")


def get_textract_client():
    """Returns Amazon Textract client configured from env."""
    return get_boto_session().client("textract")


def get_gemini_client():
    """Returns an initialized google.genai Client using GEMINI_API_KEY."""
    from google import genai
    api_key = settings.GEMINI_API_KEY or None
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client()


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

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        if not response.ok:
            return []
        hits = response.json().get("hits", {}).get("hits", [])
        return hits
    except Exception as exc:
        logger.warning(f"OpenSearch query failed: {exc}")
        return []
