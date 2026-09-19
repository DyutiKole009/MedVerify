"""
Uploads API router (§12.2 POST /uploads/presign).
"""
import uuid
from fastapi import APIRouter
from fastapi import HTTPException, status

from src.models.schemas import PresignUploadRequest, PresignUploadResponse
from src.tools.aws import get_s3_client
from src.config import settings

router = APIRouter()


@router.post("/presign", response_model=PresignUploadResponse)
def get_presigned_upload_url(request: PresignUploadRequest) -> PresignUploadResponse:
    """
    Generates a secure presigned S3 PUT URL for direct client photo uploads (§9.5, §12.2).
    Uploads go to the medverify-uploads bucket.
    """
    unique_id = str(uuid.uuid4())
    safe_filename = request.filename.replace(" ", "_")
    s3_key = f"packaging-photos/{unique_id}_{safe_filename}"

    s3 = get_s3_client()
    try:
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.S3_UPLOADS_BUCKET,
                "Key": s3_key,
                "ContentType": request.content_type,
            },
            ExpiresIn=3600,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to create an upload URL",
        ) from error

    return PresignUploadResponse(
        upload_url=url,
        s3_key=s3_key,
        expires_in=3600,
    )
