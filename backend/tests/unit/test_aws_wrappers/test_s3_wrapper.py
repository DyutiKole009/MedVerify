import pytest
from moto import mock_aws
import boto3
from src.aws_wrappers.s3 import S3Wrapper
from src.aws_wrappers.client_factory import clear_client_cache
from src.utils.exceptions import ResourceNotFoundException

BUCKET_NAME = "medverify-raw-documents"

@pytest.fixture(autouse=True)
def setup_s3():
    with mock_aws():
        clear_client_cache()
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET_NAME)
        yield

def test_put_and_get_object():
    wrapper = S3Wrapper()
    content = b"PDF dummy content"
    key = "nsq-pdfs/2026-09/alert.pdf"

    res = wrapper.put_object(BUCKET_NAME, key, content, content_type="application/pdf")
    assert res is not None

    retrieved_bytes = wrapper.get_object_bytes(BUCKET_NAME, key)
    assert retrieved_bytes == content

def test_object_exists_and_delete():
    wrapper = S3Wrapper()
    key = "test_key.txt"
    assert wrapper.object_exists(BUCKET_NAME, key) is False

    wrapper.put_object(BUCKET_NAME, key, "hello world")
    assert wrapper.object_exists(BUCKET_NAME, key) is True

    wrapper.delete_object(BUCKET_NAME, key)
    assert wrapper.object_exists(BUCKET_NAME, key) is False

def test_get_nonexistent_object():
    wrapper = S3Wrapper()
    with pytest.raises(ResourceNotFoundException):
        wrapper.get_object_bytes(BUCKET_NAME, "missing_key.pdf")

def test_presigned_url():
    wrapper = S3Wrapper()
    url = wrapper.generate_presigned_url(BUCKET_NAME, "upload.jpg", client_method="put_object")
    assert "upload.jpg" in url
    assert BUCKET_NAME in url

def test_copy_object():
    wrapper = S3Wrapper()
    wrapper.put_object(BUCKET_NAME, "src.txt", "data to copy")
    wrapper.copy_object(BUCKET_NAME, "src.txt", BUCKET_NAME, "dst.txt")

    assert wrapper.object_exists(BUCKET_NAME, "dst.txt") is True
    assert wrapper.get_object_bytes(BUCKET_NAME, "dst.txt") == b"data to copy"

def test_list_objects():
    wrapper = S3Wrapper()
    wrapper.put_object(BUCKET_NAME, "notices/2026-08/doc1.txt", "doc1")
    wrapper.put_object(BUCKET_NAME, "notices/2026-09/doc2.txt", "doc2")
    wrapper.put_object(BUCKET_NAME, "other/doc3.txt", "doc3")

    keys = wrapper.list_objects(BUCKET_NAME, prefix="notices/")
    assert len(keys) == 2
    assert "notices/2026-08/doc1.txt" in keys
    assert "notices/2026-09/doc2.txt" in keys
