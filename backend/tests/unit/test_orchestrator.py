import pytest
import json
from unittest.mock import patch, MagicMock
from src.agents.orchestrator import orchestrate, fallback_decision, OrchestratorDecision


def test_short_circuit_direct_batch():
    decision = orchestrate(batch_no="B12345")
    assert decision.selected_tier == "SKILL"
    assert decision.intent == "batch_lookup"
    assert decision.complexity == "LOW"


def test_fallback_with_image():
    decision = fallback_decision(has_image=True, raw_input="sample photo")
    assert decision.selected_tier == "REACTIVE"
    assert decision.intent == "medicine_verification"
    assert decision.known_workflow is True


def test_fallback_text_only():
    decision = fallback_decision(has_image=False, raw_input="Paracetamol")
    assert decision.selected_tier == "SKILL"
    assert decision.intent == "batch_lookup"


@patch("src.agents.orchestrator.get_orchestrator_agent")
def test_orchestrate_with_strands_deep(mock_get_agent):
    mock_agent = MagicMock()
    expected_response = OrchestratorDecision(
        intent="open_investigation",
        complexity="HIGH",
        ambiguity="HIGH",
        known_workflow=False,
        capabilities_required=5,
        selected_tier="DEEP",
        reasoning="User reports unusual side effect and suspected counterfeit blister pack."
    )
    mock_result = MagicMock()
    mock_result.structured_output = expected_response
    mock_agent.return_value = mock_result
    mock_get_agent.return_value = mock_agent

    decision = orchestrate(text="I took this medicine and developed a severe rash, the foil looks unusual.")
    assert decision.selected_tier == "DEEP"
    assert decision.complexity == "HIGH"
    assert decision.intent == "open_investigation"


@patch("src.agents.orchestrator.get_orchestrator_agent")
def test_orchestrate_error_fallback(mock_get_agent):
    mock_agent = MagicMock()
    mock_agent.side_effect = RuntimeError("Rate limit exceeded")
    mock_get_agent.return_value = mock_agent

    decision = orchestrate(text="Is this fake?", has_image=True)
    assert decision.selected_tier == "REACTIVE"
    assert "Fallback applied" in decision.reasoning or "Classification error" in decision.reasoning
