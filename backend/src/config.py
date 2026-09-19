"""
Central configuration for MedVerify backend loaded directly from .env using python-dotenv.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Locate and load .env file
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
ENV_EXAMPLE_PATH = Path(__file__).resolve().parent.parent / ".env.example"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
elif ENV_EXAMPLE_PATH.exists():
    load_dotenv(dotenv_path=ENV_EXAMPLE_PATH)


class Settings:
    """
    Configuration loaded directly from .env via python-dotenv.
    Attributes are read dynamically from os.environ.
    """
    # Type hints for editor autocomplete
    AWS_REGION: str
    AWS_ACCESS_KEY_ID: str | None
    AWS_SECRET_ACCESS_KEY: str | None
    AWS_SESSION_TOKEN: str | None

    DYNAMODB_BATCHES_TABLE: str
    DYNAMODB_REPORTS_TABLE: str
    DYNAMODB_SESSIONS_TABLE: str
    DYNAMODB_MANUFACTURERS_TABLE: str
    DYNAMODB_INGESTED_DOCS_TABLE: str

    S3_RAW_DOCUMENTS_BUCKET: str
    S3_UPLOADS_BUCKET: str
    S3_KB_DOCUMENTS_BUCKET: str

    BEDROCK_ORCHESTRATOR_MODEL_ID: str
    BEDROCK_VISION_MODEL_ID: str
    BEDROCK_SYNTHESIS_MODEL_ID: str
    BEDROCK_DEEP_AGENT_MODEL_ID: str

    BEDROCK_KB_ID: str
    BEDROCK_KB_DATA_SOURCE_NOTICES_ID: str
    BEDROCK_KB_DATA_SOURCE_CASES_ID: str
    AGENTCORE_MEMORY_ID: str

    STATE_MACHINE_REACTIVE_ARN: str
    EVENT_BUS_NAME: str
    SNS_ALERTS_TOPIC_ARN: str
    COGNITO_USER_POOL_ID: str
    COGNITO_APP_CLIENT_ID: str
    OPENSEARCH_ENDPOINT: str
    OPENSEARCH_INDEX_DRUGS: str

    ENVIRONMENT: str
    LOG_LEVEL: str
    CORS_ORIGINS: list

    def __getattr__(self, name: str):
        val = os.getenv(name)
        if name == "AWS_REGION" and not val:
            return "us-east-1"
        if name == "CORS_ORIGINS":
            try:
                return json.loads(val) if val else ["*"]
            except Exception:
                return ["*"]
        if val is not None and (val.startswith("[") or val.startswith("{")):
            try:
                return json.loads(val)
            except Exception:
                pass
        return val

    def get(self, name: str, default=None):
        val = getattr(self, name, None)
        return val if val is not None else default


settings = Settings()
