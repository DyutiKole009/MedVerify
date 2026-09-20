"""
Agent registry — dispatch by orchestrator tier.
"""
from src.agents.orchestrator import OrchestratorDecision
from src.agents.skill_agent import run_skill_agent
from src.agents.reactive_agent import run_reactive_agent
from src.agents.deep_agent import run_deep_agent


def dispatch(decision: OrchestratorDecision, **kwargs):
    """
    Route to the correct agent based on the orchestrator's selected_tier.
    kwargs are forwarded to the agent (e.g. image_s3_key, batch_no, drug_name, etc.)
    """
    tier = decision.selected_tier

    if tier == "SKILL":
        return run_skill_agent(**kwargs)

    if tier == "REACTIVE":
        return run_reactive_agent(**kwargs)

    if tier == "DEEP":
        return run_deep_agent(**kwargs)

    raise ValueError(f"Unknown tier: {tier}")
