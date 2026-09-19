"""
Central configuration for MedVerify backend loaded from environment variables and .env.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
class Settings(BaseSettings):
    # AWS Core
    AWS_REGION: str
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None

    # DynamoDB Tables
    DYNAMODB_BATCHES_TABLE: str
    DYNAMODB_REPORTS_TABLE: str
    DYNAMODB_SESSIONS_TABLE: str
    DYNAMODB_MANUFACTURERS_TABLE: str
    DYNAMODB_INGESTED_DOCS_TABLE: str

    # S3 Buckets
    S3_RAW_DOCUMENTS_BUCKET: str
    S3_UPLOADS_BUCKET: str
    S3_KB_DOCUMENTS_BUCKET: str

    # Bedrock Models
    BEDROCK_ORCHESTRATOR_MODEL_ID: str
    BEDROCK_VISION_MODEL_ID: str
    BEDROCK_SYNTHESIS_MODEL_ID: str
    BEDROCK_DEEP_AGENT_MODEL_ID: str

    # Bedrock Knowledge Base & Memory
    BEDROCK_KB_ID: str
    BEDROCK_KB_DATA_SOURCE_NOTICES_ID: Optional[str] = None
    BEDROCK_KB_DATA_SOURCE_CASES_ID: Optional[str] = None
    AGENTCORE_MEMORY_ID: Optional[str] = None

    # Step Functions
    STATE_MACHINE_REACTIVE_ARN: str

    # EventBridge & SNS
    EVENT_BUS_NAME: str
    SNS_ALERTS_TOPIC_ARN: str

    # Cognito
    COGNITO_USER_POOL_ID: Optional[str] = None
    COGNITO_APP_CLIENT_ID: Optional[str] = None

    # OpenSearch Serverless
    OPENSEARCH_ENDPOINT: str
    OPENSEARCH_INDEX_DRUGS: str

    # Server Settings
    ENVIRONMENT: str
    LOG_LEVEL: str
    CORS_ORIGINS: List[str]

    model_config = SettingsConfigDict(
        env_file=(str(ENV_PATH), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
