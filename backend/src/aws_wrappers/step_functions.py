"""
AWS Step Functions wrapper for launching and monitoring Reactive Agent verification workflows.
"""
from typing import Dict, Any, Optional
import json
from src.aws_wrappers.base import BaseAWSWrapper, catch_aws_errors
from src.aws_wrappers.client_factory import get_boto_client
from src.utils.logger import logger

class StepFunctionsWrapper(BaseAWSWrapper):
    """Encapsulates AWS Step Functions executions for the Reactive Agent (§9.3)."""
    def __init__(self):
        super().__init__("StepFunctions")
        self.client = get_boto_client("stepfunctions")

    @catch_aws_errors("StartExecution")
    def start_execution(
        self,
        state_machine_arn: str,
        input_data: Dict[str, Any],
        execution_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Starts an asynchronous execution of the Reactive Agent verification state machine.
        """
        kwargs: Dict[str, Any] = {
            "stateMachineArn": state_machine_arn,
            "input": json.dumps(input_data)
        }
        if execution_name:
            kwargs["name"] = execution_name

        response = self.client.start_execution(**kwargs)
        logger.info(f"Started Step Function execution: {response.get('executionArn')}")
        return {
            "execution_arn": response.get("executionArn"),
            "start_date": response.get("startDate").isoformat() if response.get("startDate") else None
        }

    @catch_aws_errors("DescribeExecution")
    def describe_execution(self, execution_arn: str) -> Dict[str, Any]:
        """
        Checks the status of an active or completed Step Function execution.
        """
        response = self.client.describe_execution(executionArn=execution_arn)
        status = response.get("status")
        output = None
        if "output" in response:
            try:
                output = json.loads(response["output"])
            except json.JSONDecodeError:
                output = response["output"]

        return {
            "status": status,
            "output": output,
            "error": response.get("error"),
            "cause": response.get("cause"),
            "start_date": response.get("startDate").isoformat() if response.get("startDate") else None,
            "stop_date": response.get("stopDate").isoformat() if response.get("stopDate") else None
        }

    @catch_aws_errors("StopExecution")
    def stop_execution(
        self,
        execution_arn: str,
        error: Optional[str] = None,
        cause: Optional[str] = None
    ) -> bool:
        """Terminates a running execution."""
        kwargs: Dict[str, Any] = {"executionArn": execution_arn}
        if error:
            kwargs["error"] = error
        if cause:
            kwargs["cause"] = cause
        self.client.stop_execution(**kwargs)
        return True
