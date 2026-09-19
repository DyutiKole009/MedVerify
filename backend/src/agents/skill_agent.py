"""Strands Skill Agent for one-shot deterministic lookups."""
from typing import Any

from src.config import settings
from src.tools.skill_tools import SKILL_TOOLS


def create_skill_agent(**kwargs: Any) -> Any:
    """Create a Strands agent restricted to the Skill Agent tools."""
    try:
        from strands import Agent
    except ImportError as error:
        raise RuntimeError("Install strands-agents to create the Skill Agent") from error

    return Agent(
        model=kwargs.pop("model", settings.BEDROCK_ORCHESTRATOR_MODEL_ID),
        tools=SKILL_TOOLS,
        system_prompt=kwargs.pop(
            "system_prompt",
            "You are the MedVerify Skill Agent. Make exactly one lookup tool call, then return its result. Do not investigate or invent evidence.",
        ),
        **kwargs,
    )


def run_skill_agent(prompt: str, **kwargs: Any) -> Any:
    """Run one Skill Agent request."""
    return create_skill_agent(**kwargs)(prompt)