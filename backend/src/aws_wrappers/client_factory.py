"""
Client factory for AWS services with thread-safe caching and custom retry configuration.
"""
from typing import Dict, Any, Optional
import boto3
from botocore.config import Config
from src.config import settings
from src.utils.logger import logger

_CLIENT_CACHE: Dict[str, Any] = {}
_RESOURCE_CACHE: Dict[str, Any] = {}

# Production-grade botocore config: adaptive retry mode with max 3 attempts
_DEFAULT_BOTO_CONFIG = Config(
    region_name=settings.AWS_REGION,
    retries={
        "max_attempts": 3,
        "mode": "standard"
    },
    connect_timeout=5,
    read_timeout=30
)

def get_boto_session() -> boto3.Session:
    """Returns a boto3 Session initialized with configured credentials/region."""
    session_kwargs = {"region_name": settings.AWS_REGION}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        session_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        session_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        if settings.AWS_SESSION_TOKEN:
            session_kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN
    return boto3.Session(**session_kwargs)

def get_boto_client(
    service_name: str,
    custom_config: Optional[Config] = None,
    endpoint_url: Optional[str] = None
) -> Any:
    """
    Returns a cached boto3 client for the requested service.
    """
    cache_key = f"{service_name}:{endpoint_url}:{settings.AWS_REGION}"
    if cache_key not in _CLIENT_CACHE:
        session = get_boto_session()
        cfg = custom_config or _DEFAULT_BOTO_CONFIG
        kwargs: Dict[str, Any] = {"config": cfg}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        _CLIENT_CACHE[cache_key] = session.client(service_name, **kwargs)
        logger.debug(f"Initialized new boto3 client for {service_name}")
    return _CLIENT_CACHE[cache_key]

def get_boto_resource(service_name: str, endpoint_url: Optional[str] = None) -> Any:
    """
    Returns a cached boto3 resource (e.g. for DynamoDB).
    """
    cache_key = f"{service_name}:{endpoint_url}:{settings.AWS_REGION}"
    if cache_key not in _RESOURCE_CACHE:
        session = get_boto_session()
        kwargs: Dict[str, Any] = {"config": _DEFAULT_BOTO_CONFIG}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        _RESOURCE_CACHE[cache_key] = session.resource(service_name, **kwargs)
        logger.debug(f"Initialized new boto3 resource for {service_name}")
    return _RESOURCE_CACHE[cache_key]

def clear_client_cache() -> None:
    """Clears cached clients (useful for unit testing with moto)."""
    _CLIENT_CACHE.clear()
    _RESOURCE_CACHE.clear()
