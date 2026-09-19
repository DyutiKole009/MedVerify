"""
Agent registry — dispatch by orchestrator tier.
"""
from src.agents.orchestrator import OrchestratorDecision
from src.agents.skill_agent import run_skill_agent
from src.agents.reactive_agent import run_reactive_agent


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
        # Deep agent requires Bedrock — return a stub result until model access is available
        from src.tools.skill_tools import check_batch, get_community_reports, get_manufacturer_history
        batch_no   = kwargs.get("batch_no")
        drug_name  = kwargs.get("drug_name")
        mfg        = kwargs.get("manufacturer_name", "")
        checks = {
            "batch":        check_batch(batch_no or "", drug_name, mfg),
            "community":    get_community_reports(batch_no, drug_name),
            "manufacturer": get_manufacturer_history(mfg),
        }
        return {
            "tier": "DEEP",
            "status": "PARTIAL",
            "note": "Deep agent requires Bedrock model access. Returning evidence-only result.",
            "checks": checks,
        }

    raise ValueError(f"Unknown tier: {tier}")