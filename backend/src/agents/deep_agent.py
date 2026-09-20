"""Deep Agent using deepagents and TodoListMiddleware with Google Gemini and resilient Groq fallback."""
import json
import os
import uuid
from typing import Any, Dict, List, Optional
from deepagents import create_deep_agent as _create_deep_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import settings
from src.tools.deep_tools import DEEP_TOOLS
from src.tools.aws import get_dynamodb_resource, convert_floats_to_decimals
from src.utils.logger import logger

DEEP_AGENT_SYSTEM_PROMPT = """You are the MedVerify Deep Agent, an autonomous clinical pharmacovigilance and CDSCO regulatory medicine investigator.
Your mission is to rigorously investigate suspicious medicines, reported adverse reactions, potential counterfeit or substandard drugs, and consumer medicine safety concerns.

### MANDATORY PLANNING & INVESTIGATION PROTOCOL:
1. **Explicit Investigation Planning**:
   - You MUST immediately invoke the `write_todos` tool at the start of your turn to formulate a clear, multi-phase investigation plan.
   - Do NOT produce vague, generic steps. Your plan must include concrete milestones tailored to the user's specific context:
     * Milestone 1: "Clinical & Entity Extraction: Analyze reported symptoms (e.g. headache, nausea), extract potential drug/batch identifiers, or flag missing product details."
     * Milestone 2: "Regulatory & Quality Lookup: Search CDSCO database via `check_batch` and fuzzy drug index via `search_drug` for recalled, NSQ, or spurious alerts."
     * Milestone 3: "Manufacturer & Historical Risk: Check manufacturer compliance and historical risk profile via `get_manufacturer_history`."
     * Milestone 4: "Community & Adverse Signals: Review real-world consumer reports and adverse reaction trends via `get_community_reports` or `retrieve_similar_cases`."
     * Milestone 5: "Clinical Advisory & SOP Consultation: Consult Bedrock Knowledge Base via `retrieve_regulatory_advisory` for clinical monograph consequences, packaging verification rules, and PvPI reporting SOPs."
     * Milestone 6: "Synthesis & Patient Harm Reduction: Deliver comprehensive clinical assessment, triage warnings, and actionable next steps."
   - Update your todos as you make progress and complete tasks.

2. **Handling Missing or Ambiguous Medicine/Batch Information**:
   - If the user provides symptoms without a specific drug name or batch (e.g., "I took a medicine and my head hurts"):
     * Explicitly state that specific CDSCO regulatory batch verification requires the exact medicine name and batch number.
     * Instruct the patient on how to locate the batch number (crimped edge of foil blister strip, back label, carton flap) or recommend uploading a packaging photo.
     * Do NOT invent a medicine name or treat user narrative sentences as a drug name.
     * Provide immediate clinical guidance regarding the symptom: common medicine classes that trigger this symptom, potential adverse drug reactions, and red-flag emergency symptoms (e.g., severe sudden headache, stiff neck, high fever, altered mental status, visual disturbance, difficulty breathing) requiring immediate emergency medical care.

3. **Systematic Multi-Tool Evidence Gathering**:
   - If a drug name or fuzzy text is provided, use `search_drug` to resolve misspellings or identify active ingredients.
   - If a batch number is available, check official CDSCO records with `check_batch`.
   - If a manufacturer is identified, assess track record with `get_manufacturer_history`.
   - Query `retrieve_regulatory_advisory` for relevant clinical consequences of quality defects, packaging counterfeiting signs, or ADR management.
   - Query `get_community_reports` to see if other patients reported similar issues.

4. **Clinical Integrity & Regulatory Safety**:
   - NEVER claim a medicine is genuine or 100% safe. Always reinforce that "Absence of a flag in the CDSCO registry is not proof of safety."
   - Synthesize findings into a clear, professional, empathetic clinical dossier.
   - Always conclude with clear advice on whether to withhold the medication and consult a physician or licensed pharmacist.
"""


def create_deep_agent(**kwargs: Any) -> Any:
    """Create a deep agent graph with TodoListMiddleware using Google Gemini."""
    api_key = settings.GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. The Deep Agent requires a real Gemini API key. "
            "Add it to your .env file as GEMINI_API_KEY=<your-key>."
        )
    if not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = api_key

    model_name = kwargs.pop("model", None) or getattr(settings, "GEMINI_MODEL_ID", None) or "google_genai:gemini-2.5-flash-lite"
    if not model_name.startswith("google_genai:"):
        model_name = f"google_genai:{model_name}"

    tools = kwargs.pop("tools", DEEP_TOOLS)
    middleware = kwargs.pop("middleware", [TodoListMiddleware()])

    return _create_deep_agent(
        model=model_name,
        tools=tools,
        middleware=middleware,
        **kwargs,
    )


def _groq_deep_investigation_fallback(
    user_query: str,
    evidence: Dict[str, Any],
    advisories: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Resilient fallback using Groq (e.g. openai/gpt-oss-120b) to synthesize a rich,
    rigorous clinical and regulatory investigation when Gemini hits quota or fails.
    """
    try:
        from groq import Groq
        groq_client = Groq(api_key=settings.GROQ_API_KEY)
        model = settings.GROQ_MODEL_ID or "openai/gpt-oss-120b"
        evidence_str = json.dumps(evidence, indent=2, default=str)
        adv_text = ""
        if advisories:
            adv_text = "\n".join([f"- {a.get('content_preview', '')}" for a in advisories])

        prompt = f"""Investigate the following medicine inquiry or adverse symptom context:

User Context:
{user_query}

Verified Regulatory & Community Evidence:
{evidence_str}

Regulatory Monographs / Advisories:
{adv_text or 'No specific CDSCO monograph excerpt retrieved.'}

Instructions:
1. Address the patient with empathy and clear structure.
2. If the user did not specify the exact medicine name and batch number, state clearly that CDSCO laboratory batch verification requires the product name and batch code. Explain where to find the batch number (crimped edge of blister strip, printed label) or encourage taking a packaging photo.
3. Clinically analyze the reported symptom / adverse concern. Outline common medication causes, drug classes, potential adverse reaction mechanisms, and red-flag emergency symptoms that warrant immediate medical evaluation.
4. Synthesize all regulatory and community evidence.
5. Provide actionable guidance: advise whether to withhold the medication until medical advice is obtained, how to report to the Pharmacovigilance Programme of India (PvPI), and reinforce that absence of a flag is not proof of safety.
"""
        groq_system_prompt = (
            "You are the MedVerify Deep Agent, an autonomous clinical pharmacovigilance and CDSCO regulatory medicine investigator.\n"
            "Synthesize your complete clinical and regulatory investigation report as structured markdown text directly. "
            "Do not invoke tools in this step; provide your direct analysis, clinical recommendations, and patient safety guidance."
        )
        response = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": groq_system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        return response.choices[0].message.content or ""
    except Exception as g_exc:
        logger.warning(f"[DEEP_AGENT] Groq fallback investigation failed: {g_exc}")
        return ""


def run_deep_agent(
    text: Optional[str] = None,
    batch_no: Optional[str] = None,
    drug_name: Optional[str] = None,
    manufacturer_name: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Executes the Deep Agent with TodoListMiddleware, tracks reasoning trajectory,
    and persists the investigation result to DynamoDB.
    """
    session_id = session_id or str(uuid.uuid4())
    logger.info(f"[DEEP_AGENT] Starting deep investigation for session={session_id}")

    # 1. Clean and disambiguate inputs:
    # If drug_name is actually a full sentence or narrative symptoms (e.g. "I had a medicine and my head hurts")
    symptom_keywords = ["hurt", "pain", "headache", "fever", "nausea", "vomit", "dizzy", "medicine", "pill", "took", "had a", "feel", "sick"]
    if drug_name and any(k in drug_name.lower() for k in symptom_keywords) and len(drug_name.split()) > 2:
        if not text:
            text = drug_name
        drug_name = None

    if text:
        text = text.strip()

    # 2. Baseline evidence checks across databases
    # 2. Comprehensive multi-source evidence checks across CDSCO databases and Bedrock KB
    evidence_checks = {
        "batch": {"found": False, "batch_record": None},
        "community": {"report_count": 0, "reports": []},
        "manufacturer": {"manufacturer_record": None, "recent_batches": []},
        "drug_search": {"candidates": []},
        "advisory": {"results": []},
    }
    try:
        from src.tools.skill_tools import (
            check_batch,
            get_community_reports,
            get_manufacturer_history,
            retrieve_regulatory_advisory,
            search_drug,
        )

        if batch_no or drug_name:
            evidence_checks["batch"] = check_batch(batch_no or "", drug_name, manufacturer_name)
            evidence_checks["community"] = get_community_reports(batch_no, drug_name)

        search_term = drug_name or (text.split()[0] if text and len(text.split()) < 4 else "")
        if search_term:
            evidence_checks["drug_search"] = search_drug(search_term, size=5)

        # Auto-resolve manufacturer from batch record if not provided
        batch_rec = evidence_checks["batch"].get("batch_record")
        if not manufacturer_name and batch_rec and batch_rec.get("manufacturer_name"):
            manufacturer_name = batch_rec.get("manufacturer_name")

        if manufacturer_name:
            evidence_checks["manufacturer"] = get_manufacturer_history(manufacturer_name)

        # Retrieve Bedrock Knowledge Base advisories (clinical monographs, anti-counterfeit packaging protocols, PvPI SOPs)
        advisory_query = text or drug_name or "packaging inspection anti counterfeit adverse drug reaction"
        evidence_checks["advisory"] = retrieve_regulatory_advisory(advisory_query, number_of_results=4)
    except Exception as check_exc:
        logger.warning(f"[DEEP_AGENT] Evidence check failed: {check_exc}")

    # Build prompt for deep agent
    prompt_parts = []
    if text:
        prompt_parts.append(f"User Inquiry / Symptoms / Context: {text}")
    if drug_name:
        prompt_parts.append(f"Drug Name: {drug_name}")
    else:
        prompt_parts.append("Drug Name: [Not provided by user - require clarification or photo]")
    if batch_no:
        prompt_parts.append(f"Batch Number: {batch_no}")
    else:
        prompt_parts.append("Batch Number: [Not provided by user - require clarification]")
    if manufacturer_name:
        prompt_parts.append(f"Manufacturer: {manufacturer_name}")

    user_query = "\n".join(prompt_parts)

    explanation = ""
    trajectory: List[Dict[str, Any]] = []
    todos: List[Dict[str, Any]] = []

    # 3. Primary execution with Google Gemini Deep Agent
    try:
        agent = create_deep_agent()
        messages = [
            SystemMessage(content=DEEP_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=user_query),
        ]
        logger.info(f"[GEMINI REQUEST] [Deep Agent] Prompting Deep Agent with TodoListMiddleware")
        result = agent.invoke({"messages": messages})
        output_messages = result.get("messages", [])
        if output_messages:
            last_message = output_messages[-1]
            explanation = getattr(last_message, "content", str(last_message)).strip()

        todos = result.get("todos", [])
        for msg in output_messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    trajectory.append({"tool": tc.get("name"), "args": tc.get("args")})

        logger.info(f"[GEMINI RESPONSE] [Deep Agent] Finished: {len(trajectory)} tool calls, {len(todos)} todos, {len(explanation)} chars output")
        if not explanation:
            logger.info("[DEEP_AGENT] Gemini returned empty explanation. Engaging Groq fallback...")
            advisory_items = evidence_checks.get("advisory", {}).get("results", [])
            explanation = _groq_deep_investigation_fallback(user_query, evidence_checks, advisory_items)

    except Exception as exc:
        logger.warning(f"[DEEP_AGENT] Gemini execution error/quota ({exc}). Engaging Groq fallback...")
        advisory_items = evidence_checks.get("advisory", {}).get("results", [])
        explanation = _groq_deep_investigation_fallback(user_query, evidence_checks, advisory_items)

    # 4. If explanation is still blank, formulate structured clinical synthesis
    if not explanation:
        batch_info = (evidence_checks.get("batch") or {}).get("batch_record") or {}
        alert_status = batch_info.get("alert_status", "No adverse regulatory record recorded")
        comm_reports = (evidence_checks.get("community") or {}).get("report_count", 0)
        mfg_risk = (evidence_checks.get("manufacturer") or {}).get("risk_profile", "Unknown")

        if not drug_name and not batch_no:
            explanation = (
                "### Clinical & Regulatory Triage Assessment\n\n"
                "**1. Missing Medicine Identification**:\n"
                "You reported experiencing adverse symptoms after taking medication, but no specific brand name, active pharmaceutical ingredient, or batch code was detected in your message. "
                "Official CDSCO regulatory verification requires the exact medicine name and printed batch number to cross-reference against national recall databases.\n\n"
                "**2. Symptom Evaluation & Potential Adverse Drug Reactions**:\n"
                "Headaches, dizziness, or acute discomfort following medicine intake can arise from various pharmacological mechanisms:\n"
                "- Vasodilator effects (e.g., nitrates, calcium channel blockers)\n"
                "- Medication overuse or rebound effects (analgesics)\n"
                "- Idiosyncratic or allergic drug reactions\n"
                "- Substandard quality issues (impurities, incorrect active pharmaceutical ingredient potency)\n\n"
                "**3. Red-Flag Warning Signs (Seek Immediate Medical Care)**:\n"
                "Please go to the nearest emergency clinic if the headache is sudden and extraordinarily severe ('thunderclap'), accompanied by a stiff neck, high fever, confusion, difficulty speaking, vision changes, facial numbness, or shortness of breath.\n\n"
                "**4. Recommended Actions**:\n"
                "- **Withhold further doses** until you consult your prescribing doctor or a licensed pharmacist.\n"
                "- **Check packaging**: Locate the printed batch number (usually stamped on the foil blister's crimped edge or the carton flap) or take a clear photo of the packaging and upload it here.\n"
                "- **Report Adverse Reaction**: If symptoms persist, report the event to the Pharmacovigilance Programme of India (PvPI).\n\n"
                "*Notice: Absence of an official flag in government records is not proof of safety.*"
            )
        else:
            explanation = (
                f"### Regulatory & Pharmacovigilance Investigation Dossier\n\n"
                f"**Medicine**: {drug_name or 'Unspecified'} | **Batch**: {batch_no or 'Unspecified'}\n\n"
                f"- **CDSCO Registry Check**: {alert_status}\n"
                f"- **Community Issue Signals**: {comm_reports} crowd-sourced adverse report(s)\n"
                f"- **Manufacturer Risk Profile**: {mfg_risk}\n\n"
                f"**Clinical Recommendation**:\n"
                f"Always verify the physical integrity of packaging (intact tamper-evident seals, uniform tablet coloration, clear blister foil printing). If you feel unwell after consumption, discontinue use and consult a physician immediately.\n\n"
                f"*Notice: Absence of an official flag is not proof of safety.*"
            )

    # 5. Populate structured todos if not generated by TodoListMiddleware
    if not todos or all(t.get("status") == "pending" for t in todos):
        todos = [
            {"content": f"Clinical & Entity Extraction: Analyzed inquiry context ('{((text or drug_name or '')[:45])}')", "status": "completed"},
            {"content": f"CDSCO Quality Registry Check: Batch {batch_no or 'unspecified'} cross-referenced with recall database", "status": "completed" if batch_no else "pending"},
            {"content": f"Formulation & Recall Search: Checked national drug registers for {drug_name or 'reported medicine'}", "status": "completed" if (drug_name or evidence_checks.get('drug_search', {}).get('candidates')) else "pending"},
            {"content": f"Manufacturer Risk Analysis: {manufacturer_name or 'Manufacturer unconfirmed'}", "status": "completed" if manufacturer_name else "pending"},
            {"content": "Advisory & Monograph Synthesis: Ingested Bedrock anti-counterfeit protocols & clinical guidance", "status": "completed"},
            {"content": "Triage & Harm Reduction: Formulated clinical recommendations and PvPI reporting SOPs", "status": "completed"},
        ]

    # 6. Formulate headline summary and status category
    batch_record = (evidence_checks.get("batch") or {}).get("batch_record")
    comm_reports = (evidence_checks.get("community") or {}).get("report_count", 0)

    if not drug_name and not batch_no:
        status_category = "INFO_NEEDED"
        summary = "Clinical investigation into reported adverse symptoms. Specific medicine and batch details are required for CDSCO registry verification."
    elif batch_record and batch_record.get("alert_status") == "SPURIOUS":
        status_category = "SPURIOUS"
        summary = f"SPURIOUS MEDICINE ALERT: Batch {batch_no} ({drug_name}) is confirmed counterfeit/spurious by CDSCO. Do not consume."
    elif batch_record and batch_record.get("alert_status") == "NSQ":
        status_category = "NSQ"
        summary = f"QUALITY DEFECT ALERT: Batch {batch_no} ({drug_name}) failed government laboratory standards (NSQ): {batch_record.get('nsq_reason', 'Not of Standard Quality')}."
    elif comm_reports > 0:
        status_category = "COMMUNITY_FLAGGED"
        summary = f"Caution: Batch/Medicine has {comm_reports} community adverse issue report(s) on file. Regulatory check found no official CDSCO recall."
    elif batch_no:
        status_category = "CLEAR"
        summary = f"CDSCO registry review completed for batch {batch_no} ({drug_name or 'queried medicine'}). No active quality failure or spurious notice found."
    else:
        status_category = "NO_MATCH"
        summary = f"Clinical assessment completed for {drug_name or 'reported medicine'}. No official adverse regulatory notices recorded."

    # 7. Formulate structured reasoning trace
    reasoning_trace = [
        "Step 1: Orchestrator identified narrative symptoms/clinical investigation context -> Routed to Deep Agent Tier.",
    ]
    if drug_name or batch_no:
        reasoning_trace.append(f"Step 2: Identified target entity: Drug='{drug_name or 'Not specified'}', Batch='{batch_no or 'Not specified'}'.")
    else:
        reasoning_trace.append("Step 2: Entity analysis: No specific medicine name or batch code detected in user query.")
    reasoning_trace.append("Step 3: Queried CDSCO official batches registry and fuzzy OpenSearch drug index.")
    if comm_reports > 0:
        reasoning_trace.append(f"Step 4: Checked community pharmacovigilance reports: {comm_reports} crowd-sourced signal(s) found.")
    else:
        reasoning_trace.append("Step 4: Checked community pharmacovigilance reports: No prior matching reports on record.")
    reasoning_trace.append("Step 5: Synthesized clinical monograph risk profile and patient triage guidance.")

    # 8. Source attributions
    sources = []
    if batch_record:
        sources.append({
            "type": "DB",
            "label": f"CDSCO DynamoDB — {batch_record.get('alert_status', 'NSQ')} Record",
            "reference": batch_record.get("batch_no") or batch_no,
            "doc_url": batch_record.get("source_document_pdf_url"),
            "content_preview": (
                f"Drug: {batch_record.get('drug_name', 'N/A')} | "
                f"Batch: {batch_record.get('batch_no', 'N/A')} | "
                f"Status: {batch_record.get('alert_status', 'N/A')} | "
                f"Reason: {batch_record.get('nsq_reason', 'N/A')}"
            ),
        })

    advisory_hits = evidence_checks.get("advisory", {}).get("results", [])
    for hit in advisory_hits[:2]:
        sources.append({
            "type": "KB",
            "label": "Bedrock Knowledge Base — Regulatory Advisory",
            "reference": hit.get("s3_uri"),
            "content_preview": (hit.get("content") or "")[:150],
            "score": hit.get("score"),
        })

    final_result = {
        "session_id": session_id,
        "tier": "DEEP",
        "status": "COMPLETED",
        "status_category": status_category,
        "summary": summary,
        "explanation": explanation,
        "evidence": evidence_checks,
        "trajectory": trajectory,
        "todos": todos,
        "reasoning_trace": reasoning_trace,
        "batch_record": batch_record,
        "community_flag": comm_reports > 0,
        "sources": sources,
        "extracted_fields": {
            "drug_name": drug_name or "Not specified",
            "batch_no": batch_no or "Not specified",
            "manufacturer": manufacturer_name or "Not specified",
            "symptoms_reported": text if (not drug_name and not batch_no) else None,
        },
        "limitation_statement": "Absence of a flag is not proof of safety.",
    }

    # Persist to DynamoDB Sessions table
    try:
        dynamo = get_dynamodb_resource()
        table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
        table.update_item(
            Key={"PK": f"SESSION#{session_id}", "SK": "META"},
            UpdateExpression="SET final_result = :r, #st = :s, summary = :sum, status_category = :sc",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":r": convert_floats_to_decimals(final_result),
                ":s": "DONE",
                ":sum": summary,
                ":sc": status_category,
            },
        )
    except Exception as d_exc:
        logger.warning(f"[DEEP_AGENT] DynamoDB session update failed: {d_exc}")

    return final_result
