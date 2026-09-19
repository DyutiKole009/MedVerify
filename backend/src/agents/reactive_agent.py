"""Strands-backed fixed workflow agent for packaging-photo verification."""
from typing import Any

from src.config import settings
from src.tools.reactive_tools import REACTIVE_TOOLS


def create_reactive_agent(**kwargs: Any) -> Any:
    """Create a Strands agent constrained to the Reactive workflow tools."""
    try:
        from strands import Agent
    except ImportError as error:
        raise RuntimeError("Install strands-agents to create the Reactive Agent") from error

    return Agent(
        model=kwargs.pop("model", settings.BEDROCK_SYNTHESIS_MODEL_ID),
        tools=REACTIVE_TOOLS,
        system_prompt=kwargs.pop(
            "system_prompt",
            """You are the MedVerify Reactive Agent. Follow this exact order: extract_from_image, normalize_and_resolve, run_parallel_checks, synthesize_evidence, store_session. Do not skip a step, add tools, or make a genuine/safe verdict.""",
        ),
        **kwargs,
    )


def run_reactive_agent(prompt: str, **kwargs: Any) -> Any:
    """Run one packaging-photo verification workflow."""
    return create_reactive_agent(**kwargs)(prompt)