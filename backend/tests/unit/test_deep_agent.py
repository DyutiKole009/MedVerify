import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from src.agents.deep_agent import create_deep_agent, run_deep_agent


def test_create_deep_agent():
    agent = create_deep_agent(model="google_genai:gemini-2.5-flash")
    assert agent is not None
    graph_nodes = agent.get_graph().nodes.keys()
    assert "TodoListMiddleware.after_model" in graph_nodes


@patch("src.agents.deep_agent.create_deep_agent")
@patch("src.agents.deep_agent.get_dynamodb_resource")
def test_run_deep_agent_success(mock_dynamo, mock_create_agent):
    mock_agent = MagicMock()
    msg = AIMessage(content="Deep investigation complete. No spurious alerts found.")
    msg.tool_calls = [{"name": "check_batch", "args": {"batch_no": "B123"}}]
    mock_agent.invoke.return_value = {
        "messages": [msg],
        "todos": [{"task": "Check batch", "status": "completed"}],
    }
    mock_create_agent.return_value = mock_agent

    mock_table = MagicMock()
    mock_dynamo.return_value.Table.return_value = mock_table

    result = run_deep_agent(batch_no="B123", text="Check suspicious package")
    assert result["tier"] == "DEEP"
    assert result["status"] == "COMPLETED"
    assert "Deep investigation complete" in result["explanation"]
    assert len(result["trajectory"]) == 1
    assert result["trajectory"][0]["tool"] == "check_batch"
    assert "Absence of a flag is not proof of safety." in result["limitation_statement"]


@patch("src.agents.deep_agent.create_deep_agent")
@patch("src.agents.deep_agent.get_dynamodb_resource")
def test_run_deep_agent_fallback(mock_dynamo, mock_create_agent):
    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = RuntimeError("Gemini quota exceeded")
    mock_create_agent.return_value = mock_agent

    mock_table = MagicMock()
    mock_dynamo.return_value.Table.return_value = mock_table

    result = run_deep_agent(batch_no="B123", text="Check suspicious package")
    assert result["tier"] == "DEEP"
    assert result["status"] == "COMPLETED"
    assert "Investigation completed using available regulatory" in result["explanation"]
