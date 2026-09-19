import pytest
from unittest.mock import MagicMock, patch
from src.aws_wrappers.bedrock_kb import BedrockKBWrapper

@pytest.fixture
def mock_clients():
    with patch("src.aws_wrappers.bedrock_kb.get_boto_client") as mock_get_client:
        mock_runtime = MagicMock()
        mock_agent = MagicMock()

        def side_effect(service_name):
            if service_name == "bedrock-agent-runtime":
                return mock_runtime
            return mock_agent

        mock_get_client.side_effect = side_effect
        yield mock_runtime, mock_agent

def test_retrieve(mock_clients):
    mock_runtime, _ = mock_clients
    mock_runtime.retrieve.return_value = {
        "retrievalResults": [
            {
                "content": {"text": "Notice excerpt regarding batch B123"},
                "location": {"s3Location": {"uri": "s3://medverify-kb-documents/notices/2026-09/doc.txt"}},
                "score": 0.89,
                "metadata": {"batch_no": "B123", "drug_name": "Paracetamol"}
            }
        ]
    }

    wrapper = BedrockKBWrapper()
    results = wrapper.retrieve(
        kb_id="test-kb-id",
        query_text="Paracetamol quality concerns",
        number_of_results=1,
        metadata_filter={"equals": {"key": "batch_no", "value": "B123"}}
    )

    assert len(results) == 1
    assert results[0]["content"] == "Notice excerpt regarding batch B123"
    assert results[0]["s3_uri"] == "s3://medverify-kb-documents/notices/2026-09/doc.txt"
    assert results[0]["score"] == 0.89
    mock_runtime.retrieve.assert_called_once()

def test_retrieve_and_generate(mock_clients):
    mock_runtime, _ = mock_clients
    mock_runtime.retrieve_and_generate.return_value = {
        "output": {"text": "Synthesized evidence answer"},
        "citations": [{"generatedResponsePart": {"textResponsePart": {"span": {"start": 0, "end": 10}}}}]
    }

    wrapper = BedrockKBWrapper()
    response = wrapper.retrieve_and_generate(
        kb_id="test-kb-id",
        model_arn="arn:aws:bedrock:us-east-1::foundation-model/claude-3-5-sonnet",
        query_text="Summarize alert for batch B123"
    )

    assert response["output_text"] == "Synthesized evidence answer"
    assert len(response["citations"]) == 1

def test_start_ingestion_job(mock_clients):
    _, mock_agent = mock_clients
    mock_agent.start_ingestion_job.return_value = {
        "ingestionJob": {
            "ingestionJobId": "job-9999",
            "status": "STARTING"
        }
    }

    wrapper = BedrockKBWrapper()
    job = wrapper.start_ingestion_job(
        kb_id="test-kb-id",
        data_source_id="test-ds-id",
        description="Daily NSQ notices sync"
    )

    assert job["ingestionJobId"] == "job-9999"
    assert job["status"] == "STARTING"
    mock_agent.start_ingestion_job.assert_called_once_with(
        knowledgeBaseId="test-kb-id",
        dataSourceId="test-ds-id",
        description="Daily NSQ notices sync"
    )
