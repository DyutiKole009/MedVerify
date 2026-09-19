"""
AWS Service Wrappers Package for MedVerify.
Exposes clean, modular interfaces to all AWS services.
"""
from src.aws_wrappers.dynamodb import DynamoDBWrapper
from src.aws_wrappers.s3 import S3Wrapper
from src.aws_wrappers.bedrock_runtime import BedrockRuntimeWrapper
from src.aws_wrappers.bedrock_kb import BedrockKBWrapper
from src.aws_wrappers.agentcore_memory import AgentCoreMemoryWrapper
from src.aws_wrappers.textract import TextractWrapper
from src.aws_wrappers.opensearch import OpenSearchWrapper
from src.aws_wrappers.step_functions import StepFunctionsWrapper
from src.aws_wrappers.eventbridge import EventBridgeWrapper
from src.aws_wrappers.sns import SNSWrapper
from src.aws_wrappers.cognito import CognitoWrapper

__all__ = [
    "DynamoDBWrapper",
    "S3Wrapper",
    "BedrockRuntimeWrapper",
    "BedrockKBWrapper",
    "AgentCoreMemoryWrapper",
    "TextractWrapper",
    "OpenSearchWrapper",
    "StepFunctionsWrapper",
    "EventBridgeWrapper",
    "SNSWrapper",
    "CognitoWrapper",
]
