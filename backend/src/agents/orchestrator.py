"""
Orchestrator classification and tier routing logic (§9.1).
Determines whether a query is resolved via SKILL, REACTIVE, or DEEP agent tiers.
"""
import json
import re
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from src.config import settings
from src.tools.aws import get_bedrock_runtime_client
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


def fallback_decision(has_image: bool, raw_input: str, reason: str = "Fallback applied") -> OrchestratorDecision:
    """Deterministic fallback when Bedrock classification fails or is unavailable (§9.1)."""
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
    Classifies user input using Bedrock and returns the selected agent tier.
    Falls back gracefully to deterministic heuristics on failure.
    """
    is_image = has_image or bool(image_s3_key)

    # Short-circuit rule 1: If an explicit batch number is given without open narrative, route to SKILL
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

    # Compose prompt for Bedrock
    user_payload = {
        "text": text or "",
        "batch_no": batch_no or "",
        "drug_name": drug_name or "",
        "manufacturer": manufacturer or "",
        "has_image": is_image,
    }

    try:
        bedrock = get_bedrock_runtime_client()
        response = bedrock.converse(
            modelId=settings.BEDROCK_ORCHESTRATOR_MODEL_ID,
            messages=[{
                "role": "user",
                "content": [{"text": json.dumps(user_payload)}]
            }],
            system=[{"text": ORCHESTRATOR_SYSTEM_PROMPT}],
            inferenceConfig={"maxTokens": 500, "temperature": 0.0},
        )
        output_text = response.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
        cleaned = _clean_json(output_text)
        data = json.loads(cleaned)
        return OrchestratorDecision(**data)
    except Exception as exc:
        logger.warning(f"Orchestrator Bedrock call failed: {exc}. Using deterministic fallback.")
        return fallback_decision(has_image=is_image, raw_input=str(user_payload), reason=f"Classification error ({exc})")
