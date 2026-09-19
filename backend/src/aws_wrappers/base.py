"""
Base wrapper class providing unified AWS error handling and telemetry.
"""
from typing import Callable, TypeVar, Any
from functools import wraps
from botocore.exceptions import ClientError, BotoCoreError
from src.utils.exceptions import (
    AWSWrapperException,
    ResourceNotFoundException,
    ConflictException,
    RateLimitException
)
from src.utils.logger import logger

F = TypeVar("F", bound=Callable[..., Any])

class BaseAWSWrapper:
    """Base class for all AWS service wrappers with standardized error translation."""
    def __init__(self, service_name: str):
        self.service_name = service_name

    def handle_aws_error(self, operation: str, error: Exception) -> None:
        """Translates botocore exceptions into strongly-typed MedVerify domain exceptions."""
        if isinstance(error, ClientError):
            code = error.response.get("Error", {}).get("Code", "Unknown")
            msg = error.response.get("Error", {}).get("Message", str(error))
            logger.error(
                f"AWS error during {self.service_name}:{operation} -> [{code}] {msg}",
                extra={"service": self.service_name, "operation": operation, "code": code}
            )

            if code in ("ResourceNotFoundException", "NoSuchKey", "NotFoundException"):
                raise ResourceNotFoundException(self.service_name, msg, error) from error
            elif code in ("ConditionalCheckFailedException", "ResourceAlreadyExistsException", "ConflictException"):
                raise ConflictException(self.service_name, msg, error) from error
            elif code in ("ThrottlingException", "RequestLimitExceeded", "ProvisionedThroughputExceededException"):
                raise RateLimitException(self.service_name, msg, error) from error
            else:
                raise AWSWrapperException(self.service_name, f"[{code}] {msg}", error) from error
        elif isinstance(error, BotoCoreError):
            logger.error(f"BotoCore connection error in {self.service_name}:{operation}: {str(error)}")
            raise AWSWrapperException(self.service_name, str(error), error) from error
        else:
            raise error

def catch_aws_errors(operation_name: str):
    """Decorator to catch and handle AWS client errors within wrapper methods."""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                if hasattr(self, "handle_aws_error"):
                    self.handle_aws_error(operation_name, e)
                raise
        return wrapper  # type: ignore
    return decorator
