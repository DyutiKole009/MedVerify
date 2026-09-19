import pytest
from unittest.mock import MagicMock, patch
import json
from io import BytesIO
from src.aws_wrappers.bedrock_runtime import BedrockRuntimeWrapper
from src.utils.exceptions import ModelInferenceException

@pytest.fixture
def mock_bedrock_client():
    with patch("src.aws_wrappers.bedrock_runtime.get_boto_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client

def test_invoke_model(mock_bedrock_client):
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps({"output": "sample text"}).encode("utf-8")
    mock_bedrock_client.invoke_model.return_value = {"body": mock_body}

    wrapper = BedrockRuntimeWrapper()
    res = wrapper.invoke_model("amazon.nova-micro-v1:0", {"input": "test"})
    assert res == {"output": "sample text"}
    mock_bedrock_client.invoke_model.assert_called_once()

def test_converse(mock_bedrock_client):
    mock_bedrock_client.converse.return_value = {
        "output": {
            "message": {
                "content": [{"text": "Converse response text"}]
            }
        }
    }

    wrapper = BedrockRuntimeWrapper()
    result = wrapper.converse(
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        messages=[{"role": "user", "content": [{"text": "Hello"}]}],
        system_prompt="You are a medical verification assistant."
    )
    assert result == "Converse response text"

def test_invoke_structured_json_clean(mock_bedrock_client):
    expected_data = {
        "intent": "batch_lookup",
        "selected_tier": "SKILL",
        "reasoning": "Standard batch search"
    }
    # Test stripping of markdown code fences: ```json ... ```
    raw_markdown = f"```json\n{json.dumps(expected_data)}\n```"
    mock_bedrock_client.converse.return_value = {
        "output": {
            "message": {
                "content": [{"text": raw_markdown}]
            }
        }
    }

    wrapper = BedrockRuntimeWrapper()
    parsed = wrapper.invoke_structured_json(
        model_id="amazon.nova-micro-v1:0",
        prompt="Classify this request"
    )
    assert parsed == expected_data
    assert parsed["selected_tier"] == "SKILL"

def test_invoke_structured_json_invalid(mock_bedrock_client):
    mock_bedrock_client.converse.return_value = {
        "output": {
            "message": {
                "content": [{"text": "This is not JSON at all."}]
            }
        }
    }

    wrapper = BedrockRuntimeWrapper()
    with pytest.raises(ModelInferenceException):
        wrapper.invoke_structured_json("amazon.nova-micro-v1:0", "Prompt")

def test_extract_from_image(mock_bedrock_client):
    mock_extraction = {
        "drug_name": "Crocin 650",
        "batch_no": "CR1004",
        "manufacturer_name": "GlaxoSmithKline",
        "confidence": "high"
    }
    mock_bedrock_client.converse.return_value = {
        "output": {
            "message": {
                "content": [{"text": json.dumps(mock_extraction)}]
            }
        }
    }

    wrapper = BedrockRuntimeWrapper()
    result = wrapper.extract_from_image(
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        image_bytes=b"fake_image_bytes",
        mime_type="image/jpeg",
        prompt="Extract medicine label details"
    )
    assert result["drug_name"] == "Crocin 650"
    assert result["batch_no"] == "CR1004"
