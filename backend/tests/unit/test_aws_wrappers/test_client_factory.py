import pytest
from src.aws_wrappers.client_factory import get_boto_client, get_boto_resource, clear_client_cache

def test_client_caching():
    clear_client_cache()
    client1 = get_boto_client("s3")
    client2 = get_boto_client("s3")
    assert client1 is client2

def test_resource_caching():
    clear_client_cache()
    res1 = get_boto_resource("dynamodb")
    res2 = get_boto_resource("dynamodb")
    assert res1 is res2

def test_clear_cache():
    client1 = get_boto_client("s3")
    clear_client_cache()
    client2 = get_boto_client("s3")
    assert client1 is not client2
