"""
Custom exceptions for MedVerify AWS wrappers and domain services.
"""
from typing import Optional, Dict, Any

class MedVerifyException(Exception):
    """Base exception for all MedVerify application errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class AWSWrapperException(MedVerifyException):
    """Base exception for errors originating from AWS service interactions."""
    def __init__(self, service_name: str, message: str, original_exception: Optional[Exception] = None):
        super().__init__(f"[{service_name}] {message}")
        self.service_name = service_name
        self.original_exception = original_exception

class ResourceNotFoundException(AWSWrapperException):
    """Raised when an AWS resource or database record is not found."""
    pass

class ConflictException(AWSWrapperException):
    """Raised when a conditional write fails or a resource conflict occurs."""
    pass

class ValidationException(AWSWrapperException):
    """Raised when input parameters or response payload validation fails."""
    pass

class RateLimitException(AWSWrapperException):
    """Raised when AWS API throttling occurs."""
    pass

class ModelInferenceException(AWSWrapperException):
    """Raised when Bedrock model invocation or structured generation fails."""
    pass

class TextractProcessingException(AWSWrapperException):
    """Raised when Textract document processing encounters an error."""
    pass
