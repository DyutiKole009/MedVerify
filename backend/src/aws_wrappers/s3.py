"""
S3 wrapper providing object storage, presigned URLs, streaming, and metadata sidecar support.
"""
from typing import Dict, Any, Optional, List, Union
from io import BytesIO
from botocore.exceptions import ClientError
from src.aws_wrappers.base import BaseAWSWrapper, catch_aws_errors
from src.aws_wrappers.client_factory import get_boto_client

class S3Wrapper(BaseAWSWrapper):
    """Encapsulates all S3 storage operations including raw documents and presigned uploads."""
    def __init__(self):
        super().__init__("S3")
        self.client = get_boto_client("s3")

    @catch_aws_errors("PutObject")
    def put_object(
        self,
        bucket: str,
        key: str,
        body: Union[bytes, str, BytesIO],
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Uploads an object with optional content type and metadata."""
        if isinstance(body, str):
            body_bytes = body.encode("utf-8")
        elif isinstance(body, BytesIO):
            body_bytes = body.getvalue()
        else:
            body_bytes = body

        kwargs: Dict[str, Any] = {
            "Bucket": bucket,
            "Key": key,
            "Body": body_bytes,
            "ContentType": content_type
        }
        if metadata:
            kwargs["Metadata"] = metadata

        return self.client.put_object(**kwargs)

    @catch_aws_errors("GetObject")
    def get_object(self, bucket: str, key: str) -> Dict[str, Any]:
        """Returns the raw S3 GetObject response dictionary."""
        return self.client.get_object(Bucket=bucket, Key=key)

    @catch_aws_errors("GetObjectBytes")
    def get_object_bytes(self, bucket: str, key: str) -> bytes:
        """Retrieves and reads the full bytes of an S3 object."""
        response = self.get_object(bucket, key)
        return response["Body"].read()

    @catch_aws_errors("GeneratePresignedUrl")
    def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        client_method: str = "put_object",
        expiration: int = 3600,
        content_type: Optional[str] = None
    ) -> str:
        """Generates a presigned URL for direct client upload or download."""
        params: Dict[str, Any] = {"Bucket": bucket, "Key": key}
        if content_type and client_method == "put_object":
            params["ContentType"] = content_type

        return self.client.generate_presigned_url(
            ClientMethod=client_method,
            Params=params,
            ExpiresIn=expiration
        )

    @catch_aws_errors("CopyObject")
    def copy_object(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Copies an object from one location to another, optionally updating metadata."""
        copy_source = {"Bucket": source_bucket, "Key": source_key}
        kwargs: Dict[str, Any] = {
            "CopySource": copy_source,
            "Bucket": dest_bucket,
            "Key": dest_key
        }
        if metadata:
            kwargs["Metadata"] = metadata
            kwargs["MetadataDirective"] = "REPLACE"

        return self.client.copy_object(**kwargs)

    @catch_aws_errors("DeleteObject")
    def delete_object(self, bucket: str, key: str) -> bool:
        """Deletes an object from S3."""
        self.client.delete_object(Bucket=bucket, Key=key)
        return True

    def object_exists(self, bucket: str, key: str) -> bool:
        """Checks if an S3 object exists using head_object."""
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    @catch_aws_errors("ListObjects")
    def list_objects(self, bucket: str, prefix: str = "", max_keys: int = 1000) -> List[str]:
        """Lists object keys matching a prefix in a bucket."""
        response = self.client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_keys)
        contents = response.get("Contents", [])
        return [item["Key"] for item in contents]
