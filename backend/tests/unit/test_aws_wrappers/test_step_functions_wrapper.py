import pytest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime
from src.aws_wrappers.step_functions import StepFunctionsWrapper

@pytest.fixture
def mock_sfn_client():
    with patch("src.aws_wrappers.step_functions.get_boto_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client

def test_start_execution(mock_sfn_client):
    mock_sfn_client.start_execution.return_value = {
        "executionArn": "arn:aws:states:us-east-1:123456:execution:sm:exec-1",
        "startDate": datetime.now()
    }
    wrapper = StepFunctionsWrapper()
    res = wrapper.start_execution("arn:aws:states:us-east-1:123456:stateMachine:sm", {"session_id": "s-1"})
    assert res["execution_arn"] == "arn:aws:states:us-east-1:123456:execution:sm:exec-1"
    mock_sfn_client.start_execution.assert_called_once()

def test_describe_execution(mock_sfn_client):
    mock_sfn_client.describe_execution.return_value = {
        "status": "SUCCEEDED",
        "output": json.dumps({"verified": True, "status_category": "NO_MATCH"}),
        "startDate": datetime.now(),
        "stopDate": datetime.now()
    }
    wrapper = StepFunctionsWrapper()
    res = wrapper.describe_execution("arn:aws:states:us-east-1:123456:execution:sm:exec-1")
    assert res["status"] == "SUCCEEDED"
    assert res["output"]["status_category"] == "NO_MATCH"

def test_stop_execution(mock_sfn_client):
    wrapper = StepFunctionsWrapper()
    assert wrapper.stop_execution("arn:aws:states:us-east-1:123456:execution:sm:exec-1") is True
    mock_sfn_client.stop_execution.assert_called_once_with(
        executionArn="arn:aws:states:us-east-1:123456:execution:sm:exec-1"
    )
