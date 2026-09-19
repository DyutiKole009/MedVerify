"""
Pydantic Request and Response Schemas for MedVerify APIs (§12).
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CheckRequest(BaseModel):
    batch_no: Optional[str] = Field(None, description="Medicine batch number from packaging")
    drug_name: Optional[str] = Field(None, description="Brand or generic drug name")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")


class CheckResponse(BaseModel):
    session_id: str
    status_category: str = Field(description="MATCH_FOUND | SPURIOUS | COMMUNITY_FLAGGED | NO_MATCH")
    batch_record: Optional[Dict[str, Any]] = None
    community_flag: bool = False
    orchestrator_decision: Dict[str, Any]
    limitation_statement: str = "Absence of a flag is not proof of safety."


class InvestigateRequest(BaseModel):
    image_s3_key: str = Field(description="Key of photo previously uploaded to S3")
    mime_type: str = "image/jpeg"


class DeepInvestigateRequest(BaseModel):
    description: str = Field(description="Free-text description of suspicion or symptoms")
    drug_name: Optional[str] = None
    batch_no: Optional[str] = None
    image_s3_key: Optional[str] = None


class ProcessingResponse(BaseModel):
    session_id: str
    status: str = "PROCESSING"
    orchestrator_decision: Optional[Dict[str, Any]] = None
    extracted_fields: Optional[Dict[str, Any]] = None
    batch_record: Optional[Dict[str, Any]] = None
    status_category: Optional[str] = None
    summary: Optional[str] = None
    reasoning_trace: Optional[List[str]] = None


class FeedbackRequest(BaseModel):
    helpful: bool
    comment: Optional[str] = None


class ReportCreateRequest(BaseModel):
    drug_name: str
    batch_no: Optional[str] = None
    manufacturer_name: Optional[str] = None
    issue_type: str = Field(
        "SIDE_EFFECT",
        description="SIDE_EFFECT | SUSPECTED_FAKE | PACKAGING_ISSUE | NO_EFFECT | OTHER"
    )
    description: str
    photo_s3_key: Optional[str] = None
    area: Optional[str] = None


class PresignUploadRequest(BaseModel):
    filename: str
    content_type: str = "image/jpeg"


class PresignUploadResponse(BaseModel):
    upload_url: str
    s3_key: str
    expires_in: int = 3600
