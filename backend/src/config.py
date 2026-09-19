"""
Central configuration for MedVerify backend loaded from environment variables and .env.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    # AWS Core
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None

    # DynamoDB Tables
    DYNAMODB_BATCHES_TABLE: str = "MedVerify_Batches"
    DYNAMODB_REPORTS_TABLE: str = "MedVerify_Reports"
    DYNAMODB_SESSIONS_TABLE: str = "MedVerify_Sessions"
    DYNAMODB_MANUFACTURERS_TABLE: str = "MedVerify_Manufacturers"
    DYNAMODB_INGESTED_DOCS_TABLE: str = "MedVerify_IngestedDocs"

    # S3 Buckets
    S3_RAW_DOCUMENTS_BUCKET: str = "medverify-raw-documents"
    S3_UPLOADS_BUCKET: str = "medverify-uploads"
    S3_KB_DOCUMENTS_BUCKET: str = "medverify-kb-documents"

    # Bedrock Models
    BEDROCK_ORCHESTRATOR_MODEL_ID: str = "amazon.nova-micro-v1:0"
    BEDROCK_VISION_MODEL_ID: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    BEDROCK_SYNTHESIS_MODEL_ID: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    BEDROCK_DEEP_AGENT_MODEL_ID: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

    # Bedrock Knowledge Base & Memory
    BEDROCK_KB_ID: str = "mock-kb-id"
    BEDROCK_KB_DATA_SOURCE_NOTICES_ID: str = "mock-ds-notices-id"
    BEDROCK_KB_DATA_SOURCE_CASES_ID: str = "mock-ds-cases-id"
    AGENTCORE_MEMORY_ID: str = "medverify-investigation-memory"

    # Step Functions
    STATE_MACHINE_REACTIVE_ARN: str = "arn:aws:states:us-east-1:123456789012:stateMachine:MedVerifyReactiveVerification"

    # EventBridge & SNS
    EVENT_BUS_NAME: str = "default"
    SNS_ALERTS_TOPIC_ARN: str = "arn:aws:sns:us-east-1:123456789012:medverify-spurious-alerts"

    # Cognito
    COGNITO_USER_POOL_ID: str = "us-east-1_mockpool"
    COGNITO_APP_CLIENT_ID: str = "mockclientid123"

    # OpenSearch Serverless
    OPENSEARCH_ENDPOINT: str = "https://example-collection.us-east-1.aoss.amazonaws.com"
    OPENSEARCH_INDEX_DRUGS: str = "medverify-drugs"

    # Server Settings
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=(str(ENV_PATH), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
