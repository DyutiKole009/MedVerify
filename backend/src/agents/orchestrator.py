"""
Orchestrator classification and tier routing logic (§9.1).
Determines whether a query is resolved via SKILL, REACTIVE, or DEEP agent tiers.
Uses Strands Agent with Groq (llama-3.3-70b-versatile).
"""
import json
import os
import re
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from src.config import settings
from src.utils.logger import logger


class OrchestratorDecision(BaseModel):
    """Structured decision output from the Orchestrator (§9.1)."""
    intent: str
    complexity: str = Field(description="LOW, MEDIUM, or HIGH")
    ambiguity: str = Field(description="LOW, MEDIUM, or HIGH")
    known_workflow: bool
    capabilities_required: int = 1
    selected_tier: str = Field(description="SKILL, REACTIVE, or DEEP")
    reasoning: str


ORCHESTRATOR_SYSTEM_PROMPT = """You are the MedVerify Tier Orchestrator.
Your sole job is to classify the user's input and select the most appropriate execution tier.

Routing Rules:
1. Text-only input containing an identifiable batch number, or an exact drug + manufacturer pair:
   - intent: "batch_lookup"
   - complexity: "LOW"
   - ambiguity: "LOW"
   - known_workflow: true
   - capabilities_required: 1
   - selected_tier: "SKILL"

2. Input includes an image or photo of medicine packaging:
   - intent: "medicine_verification"
   - complexity: "MEDIUM"
   - ambiguity: "LOW"
   - known_workflow: true
   - capabilities_required: 3
   - selected_tier: "REACTIVE"

3. Input contains narrative symptoms, suspicion of counterfeit, ambiguous free-text, or an explicit request to investigate:
   - intent: "open_investigation"
   - complexity: "HIGH"
   - ambiguity: "HIGH"
   - known_workflow: false
   - capabilities_required: 5
   - selected_tier: "DEEP"

Output Format:
You MUST respond with valid JSON ONLY matching this exact schema:
{
  "intent": "string",
  "complexity": "LOW" | "MEDIUM" | "HIGH",
  "ambiguity": "LOW" | "MEDIUM" | "HIGH",
  "known_workflow": true | false,
  "capabilities_required": integer,
  "selected_tier": "SKILL" | "REACTIVE" | "DEEP",
  "reasoning": "string"
}
"""


def _clean_json(text: str) -> str:
    """Strips markdown code blocks from model response."""
    t = text.strip()
    match = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", t)
    if match:
        return match.group(1).strip()
    return t


def get_orchestrator_agent():
    """Returns a Strands Agent configured with Groq for classification."""
    try:
        import openai
        from strands import Agent
        from strands.models.openai import OpenAIModel

        api_key = getattr(settings, "GROQ_API_KEY", None) or os.environ.get("GROQ_API_KEY", "gsk_mock")
        client = openai.Client(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
        )
        model = OpenAIModel(
            client=client,
            model_id=getattr(settings, "GROQ_MODEL_ID", None) or "llama-3.3-70b-versatile",
        )
        return Agent(
            model=model,
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            structured_output_model=OrchestratorDecision,
        )
    except Exception as e:
        logger.warning(f"Failed to initialize Strands Agent with Groq: {e}")
        return None


def fallback_decision(has_image: bool, raw_input: str, reason: str = "Fallback applied") -> OrchestratorDecision:
    """Deterministic fallback when classification fails or is unavailable (§9.1)."""
    if has_image:
        return OrchestratorDecision(
            intent="medicine_verification",
            complexity="MEDIUM",
            ambiguity="LOW",
            known_workflow=True,
            capabilities_required=3,
            selected_tier="REACTIVE",
            reasoning=f"{reason}: Image detected, falling back to fixed Reactive workflow.",
        )
    return OrchestratorDecision(
        intent="batch_lookup",
        complexity="LOW",
        ambiguity="LOW",
        known_workflow=True,
        capabilities_required=1,
        selected_tier="SKILL",
        reasoning=f"{reason}: Text query detected, falling back to instant Skill lookup.",
    )


def orchestrate(
    text: Optional[str] = None,
    batch_no: Optional[str] = None,
    drug_name: Optional[str] = None,
    manufacturer: Optional[str] = None,
    has_image: bool = False,
    image_s3_key: Optional[str] = None,
) -> OrchestratorDecision:
    """
    Classifies user input using Strands Agent + Groq and returns the selected agent tier.
    Falls back gracefully to deterministic heuristics on failure.
    """
    is_image = has_image or bool(image_s3_key)

    # Short-circuit rule: explicit batch number without narrative -> always SKILL
    if (batch_no or (drug_name and manufacturer)) and not is_image and not text:
        return OrchestratorDecision(
            intent="batch_lookup",
            complexity="LOW",
            ambiguity="LOW",
            known_workflow=True,
            capabilities_required=1,
            selected_tier="SKILL",
            reasoning="Direct batch identifier provided without narrative context.",
        )

    user_payload = {
        "text": text or "",
        "batch_no": batch_no or "",
        "drug_name": drug_name or "",
        "manufacturer": manufacturer or "",
        "has_image": is_image,
    }

    logger.info(f"[STRANDS REQUEST] [Orchestrator] Payload={user_payload}")

    try:
        agent = get_orchestrator_agent()
        if agent is not None:
            result = agent(json.dumps(user_payload))
            if hasattr(result, "structured_output") and result.structured_output:
                if isinstance(result.structured_output, OrchestratorDecision):
                    decision = result.structured_output
                    logger.info(f"[STRANDS RESPONSE] [Orchestrator] Tier='{decision.selected_tier}'")
                    return decision
                if isinstance(result.structured_output, dict):
                    decision = OrchestratorDecision(**result.structured_output)
                    logger.info(f"[STRANDS RESPONSE] [Orchestrator] Tier='{decision.selected_tier}'")
                    return decision

            msg_content = ""
            if hasattr(result, "message"):
                msg = result.message
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                    msg_content = content[0].get("text", "") if isinstance(content, list) and content else str(content)
                else:
                    msg_content = str(msg)
            elif isinstance(result, str):
                msg_content = result

            cleaned = _clean_json(msg_content)
            data = json.loads(cleaned)
            decision = OrchestratorDecision(**data)
            logger.info(f"[STRANDS RESPONSE] [Orchestrator] Tier='{decision.selected_tier}'")
            return decision

        # Direct Groq fallback if Strands Agent was not initialized
        from groq import Groq
        groq_client = Groq(api_key=settings.GROQ_API_KEY)
        model = settings.GROQ_MODEL_ID or "llama-3.3-70b-versatile"
        response = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
            temperature=0.0,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        output_text = response.choices[0].message.content or "{}"
        cleaned = _clean_json(output_text)
        data = json.loads(cleaned)
        decision = OrchestratorDecision(**data)
        return decision

    except Exception as exc:
        logger.warning(f"Orchestrator classification failed: {exc}. Using deterministic fallback.")
        return fallback_decision(has_image=is_image, raw_input=str(user_payload), reason=f"Classification error ({exc})")
