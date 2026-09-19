import pytest
from unittest.mock import patch, MagicMock
from src.tools.deep_tools import (
    retrieve_related_notices,
    retrieve_similar_cases,
    record_investigation_event,
)

@patch("src.tools.deep_tools.get_bedrock_agent_runtime_client")
def test_retrieve_related_notices(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.retrieve.return_value = {
        "retrievalResults": [
            {
                "content": {"text": "Notice of quality failure"},
                "location": {"s3Location": {"uri": "s3://bucket/notice1.txt"}},
                "score": 0.95,
            }
        ]
    }

    res = retrieve_related_notices.invoke({"query_text": "paracetamol failure"})
    assert len(res["results"]) == 1
    assert res["results"][0]["score"] == 0.95
    assert res["results"][0]["s3_uri"] == "s3://bucket/notice1.txt"

@patch("src.tools.deep_tools.get_agentcore_client")
def test_retrieve_similar_cases(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.retrieve_memory_records.return_value = {
        "memoryRecords": [{"id": "rec-1", "content": "Prior case details"}]
    }

    res = retrieve_similar_cases.invoke({"query_text": "suspected fake packaging", "actor_id": "shared"})
    assert len(res["records"]) == 1
    assert res["records"][0]["id"] == "rec-1"

@patch("src.tools.deep_tools.get_agentcore_client")
def test_record_investigation_event(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.create_event.return_value = {"eventId": "event-101"}

    res = record_investigation_event.invoke({
        "actor_id": "user-1",
        "session_id": "sess-1",
        "messages": [{"role": "assistant", "content": "Checking batch"}],
    })
    assert res["eventId"] == "event-101"
