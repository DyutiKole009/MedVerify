import pytest
from unittest.mock import MagicMock, patch
from src.aws_wrappers.agentcore_memory import AgentCoreMemoryWrapper

@pytest.fixture
def mock_agentcore_client():
    with patch("src.aws_wrappers.agentcore_memory.get_boto_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client

def test_create_event(mock_agentcore_client):
    mock_agentcore_client.create_event.return_value = {"eventId": "evt-123"}
    wrapper = AgentCoreMemoryWrapper()

    res = wrapper.create_event(
        memory_id="mem-id",
        actor_id="user-sub",
        session_id="session-456",
        messages=[{"role": "tool", "content": "Checked batch B101"}]
    )
    assert res == {"eventId": "evt-123"}
    mock_agentcore_client.create_event.assert_called_once_with(
        memoryId="mem-id",
        actorId="user-sub",
        sessionId="session-456",
        messages=[{"role": "tool", "content": "Checked batch B101"}]
    )

def test_list_events(mock_agentcore_client):
    mock_agentcore_client.list_events.return_value = {
        "events": [{"eventId": "evt-1"}, {"eventId": "evt-2"}]
    }
    wrapper = AgentCoreMemoryWrapper()
    events = wrapper.list_events("mem-id", "user-sub", "session-456")
    assert len(events) == 2
    assert events[0]["eventId"] == "evt-1"

def test_get_event(mock_agentcore_client):
    mock_agentcore_client.get_event.return_value = {
        "event": {"eventId": "evt-1", "content": "Sample"}
    }
    wrapper = AgentCoreMemoryWrapper()
    event = wrapper.get_event("mem-id", "user-sub", "session-456", "evt-1")
    assert event["event"]["eventId"] == "evt-1"

def test_retrieve_memory_records(mock_agentcore_client):
    mock_agentcore_client.retrieve_memory_records.return_value = {
        "memoryRecords": [
            {"content": {"text": "Manufacturer X previously had dissolution issues in 2025"}}
        ]
    }
    wrapper = AgentCoreMemoryWrapper()
    records = wrapper.retrieve_memory_records(
        memory_id="mem-id",
        namespace="manufacturer-patterns",
        query_text="Manufacturer X issues"
    )
    assert len(records) == 1
    assert "Manufacturer X" in records[0]["content"]["text"]
