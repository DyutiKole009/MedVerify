"""
Pydantic Request and Response Schemas for MedVerify APIs (§12).
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CheckRequest(BaseModel):
    batch_no: Optional[str] = Field(None, description="Medicine batch number from packaging")
    drug_name: Optional[str] = Field(None, description="Brand or generic drug name")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    text: Optional[str] = Field(None, description="Free-text narrative query, user question, or symptom context")


class SourceChunk(BaseModel):
    """Represents a single attributed data source returned alongside a verification result."""
    type: str = Field(description="'DB' for DynamoDB batch record, 'KB' for Bedrock Knowledge Base advisory")
    label: str = Field(description="Human-readable source label, e.g. 'CDSCO NSQ Alert · Apr 2025'")
    reference: Optional[str] = Field(None, description="Batch number (DB) or S3 URI (KB)")
    content_preview: Optional[str] = Field(None, description="First ~150 chars of KB chunk text")
    doc_url: Optional[str] = Field(None, description="Direct CDSCO PDF URL if available")
    score: Optional[float] = Field(None, description="Relevance score (KB chunks only)")


class CheckResponse(BaseModel):
    session_id: str
    status_category: str = Field(description="MATCH_FOUND | SPURIOUS | COMMUNITY_FLAGGED | NO_MATCH | INFO_NEEDED | CLEAR")
    batch_record: Optional[Dict[str, Any]] = None
    community_flag: bool = False
    orchestrator_decision: Dict[str, Any]
    limitation_statement: str = "Absence of a flag is not proof of safety."
    summary: Optional[str] = None
    explanation: Optional[str] = None
    reasoning_trace: Optional[List[str]] = None
    todos: Optional[List[Dict[str, Any]]] = None
    extracted_fields: Optional[Dict[str, Any]] = None
    sources: Optional[List["SourceChunk"]] = Field(default=None, description="Attributed data sources used to answer this query")


class InvestigateRequest(BaseModel):
    image_s3_key: str = Field(description="Key of photo previously uploaded to S3")
    mime_type: str = "image/jpeg"


class DeepInvestigateRequest(BaseModel):
    description: Optional[str] = Field(None, description="Free-text description of suspicion or symptoms")
    free_text_query: Optional[str] = Field(None, description="Alias for description")
    drug_name: Optional[str] = None
    batch_no: Optional[str] = None
    image_s3_key: Optional[str] = None

    def get_query_text(self) -> str:
        return (self.description or self.free_text_query or "").strip()


class ProcessingResponse(BaseModel):
    session_id: str
    status: str = "PROCESSING"
    orchestrator_decision: Optional[Dict[str, Any]] = None
    extracted_fields: Optional[Dict[str, Any]] = None
    batch_record: Optional[Dict[str, Any]] = None
    status_category: Optional[str] = None
    summary: Optional[str] = None
    explanation: Optional[str] = None
    reasoning_trace: Optional[List[str]] = None
    todos: Optional[List[Dict[str, Any]]] = None
    sources: Optional[List["SourceChunk"]] = Field(default=None, description="Attributed data sources used to answer this query")


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
    view_url: Optional[str] = None  # Presigned GET URL — durable image link for chat history


class SignUpRequest(BaseModel):
    email: str = Field(description="User email address")
    password: str = Field(min_length=8, description="User password (min 8 chars)")
    role: Optional[str] = Field("consumer", description="consumer | pharmacist | admin")
    name: Optional[str] = Field(None, description="Full name of the user")


class ConfirmSignUpRequest(BaseModel):
    email: str = Field(description="User email address")
    confirmation_code: str = Field(description="6-digit verification code sent by Cognito")


class LoginRequest(BaseModel):
    email: str = Field(description="User email address")
    password: str = Field(description="User password")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(description="Cognito refresh token")


class ResendCodeRequest(BaseModel):
    email: str = Field(description="User email address to resend confirmation code to")


class ForgotPasswordRequest(BaseModel):
    email: str = Field(description="User email address to request password reset")


class ConfirmForgotPasswordRequest(BaseModel):
    email: str = Field(description="User email address")
    confirmation_code: str = Field(description="Reset code sent to user email")
    new_password: str = Field(min_length=8, description="New password")


class TokenResponse(BaseModel):
    access_token: str
    id_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: int = 3600
    token_type: str = "Bearer"
    role: Optional[str] = "consumer"
    user_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None


class UserProfileResponse(BaseModel):
    user_id: str
    email: Optional[str] = None
    role: str = "consumer"
    name: Optional[str] = None
    email_verified: bool = False
