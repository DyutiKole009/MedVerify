# MedVerify — Agent Architecture & Model Call Reference

This document details how language models, agent frameworks, dynamic tool selection, and `SKILL.md` specifications are configured and invoked across the MedVerify backend.

- **Dynamic LLM Tool Selection:** The LLM decides which tools to select and invoke based on the input query; tools are not statically hardcoded in Python execution blocks.
- **Skill Agent with `SKILL.md` Specs:** The Skill Agent loads all 6 specification files in `.agents/skills/` into its system prompt, dynamically selecting the appropriate lookup tools.
- **Deep Agent:** Powered by `deepagents` + `TodoListMiddleware` using Google Gemini (`google_genai:gemini-3.6-flash`).
- **Multimodal OCR:** Powered by Google Gemini Flash (`gemini-2.5-flash`).
- **Amazon Bedrock:** Completely removed.

---

## Agent Framework & Model Matrix

| Tier / Role | Agent Framework | Underlying Model | Tool Selection Mechanism | File & Function | Description |
|---|---|---|---|---|---|
| **Tier Orchestrator** | **Strands SDK** (`strands.Agent`) | **Groq** (`llama-3.3-70b-versatile`) | LLM classification | `src/agents/orchestrator.py` (`orchestrate`) | Classifies query intent and complexity; routes to SKILL, REACTIVE, or DEEP tier with structured output |
| **Multimodal OCR** | **Google GenAI SDK** | **Gemini Flash** (`gemini-2.5-flash`) | Direct vision call | `src/tools/reactive_tools.py` (`extract_from_image`) | Inspects packaging photo bytes to extract drug name, batch number, manufacturer, and dates |
| **Reactive Agent** | **Strands SDK** (`strands.Agent`) | **Groq** (`llama-3.3-70b-versatile`) | **Dynamic LLM selection** | `src/agents/reactive_agent.py` (`run_reactive_agent`) | LLM selects tools (`extract_from_image`, `normalize_and_resolve`, `run_parallel_checks`, `synthesize_evidence`, `store_session`) |
| **Skill Agent** | **Strands SDK** (`strands.Agent`) | **Groq** (`llama-3.3-70b-versatile`) | **Dynamic LLM selection via `SKILL.md`** | `src/agents/skill_agent.py` (`run_skill_agent`) | LLM selects tools guided by all 6 `.agents/skills/*/SKILL.md` specification documents |
| **Deep Agent** | **`deepagents`** + **`TodoListMiddleware`** | **Gemini** (`google_genai:gemini-3.6-flash`) | **Dynamic LLM multi-step investigation** | `src/agents/deep_agent.py` (`create_deep_agent`, `run_deep_agent`) | Autonomous clinical investigator using `TodoListMiddleware` to plan sub-tasks and execute with 8 tools |

---

## 1. Skill Agent & `SKILL.md` Integration

### 1.1 How `SKILL.md` Files Are Used
The module [`backend/src/tools/skill_docs.py`](file:///c:/Users/Dyuti%20Kole/Desktop/MedVerify/MedVerify/backend/src/tools/skill_docs.py) scans the `.agents/skills/` directory and loads all skill documents:
1. `check-batch/SKILL.md` — Direct CDSCO regulatory quality records (NSQ / spurious alerts) lookup.
2. `get-community-reports/SKILL.md` — Crowd-sourced adverse reactions and counterfeit flags.
3. `get-manufacturer-history/SKILL.md` — Risk profile, incident counters, and recent flagged batches.
4. `search-drug/SKILL.md` — OpenSearch fuzzy resolution for OCR typos or partial names.
5. `get-notice/SKILL.md` — Raw CDSCO gazette alert document text from S3.
6. `get-case-history/SKILL.md` — Prior verification sessions and user feedback history.

### 1.2 System Prompt Construction
The full markdown content from these 6 files is embedded into the Skill Agent system prompt:
```python
from src.tools.skill_docs import build_skills_system_prompt

agent = Agent(
    model=model,
    tools=SKILL_TOOLS,
    system_prompt=build_skills_system_prompt(),
)
```

### 1.3 Dynamic Tool Execution Loop
When `agent(user_query)` is called:
1. The LLM reads the user input (e.g. batch number, drug name, symptoms).
2. **The LLM decides which tool(s) to select:**
   - If a batch number is present, it invokes `check_batch`.
   - If OCR text is ambiguous or misspelled, it invokes `search_drug`.
   - It checks crowd safety signals with `get_community_reports`.
   - It evaluates the manufacturer track record with `get_manufacturer_history`.
3. Strands executes the tools selected by the LLM and feeds the outputs back into the conversation.
4. The LLM synthesizes the clinical findings into a concise consumer summary.
5. If the LLM call fails or times out, the agent falls back to baseline tool lookups.

---

## 2. Reactive Agent Dynamic Tool Execution

In [`backend/src/agents/reactive_agent.py`](file:///c:/Users/Dyuti%20Kole/Desktop/MedVerify/MedVerify/backend/src/agents/reactive_agent.py):
The Reactive Agent is equipped with all 5 verification tools (`extract_from_image`, `normalize_and_resolve`, `run_parallel_checks`, `synthesize_evidence`, and `store_session`).
The LLM dynamically triggers each step in sequence based on the extracted intermediate results, terminating with `store_session` to persist the verified state to DynamoDB.

---

## 3. Deep Agent (`deepagents` + `TodoListMiddleware`)

In [`backend/src/agents/deep_agent.py`](file:///c:/Users/Dyuti%20Kole/Desktop/MedVerify/MedVerify/backend/src/agents/deep_agent.py):
```python
from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware

agent = create_deep_agent(
    model="google_genai:gemini-3.6-flash",
    tools=DEEP_TOOLS,
    middleware=[TodoListMiddleware()],
)
```
- Uses `TodoListMiddleware` to create structured sub-tasks before tool invocation.
- Bounded to a maximum of 8 tool calls with full trajectory recording into DynamoDB.
- Asynchronous execution via FastAPI `BackgroundTasks` on `POST /investigate/deep`.

---

## 4. Environment Variables

```ini
# Groq (Orchestrator, Reactive Agent, Skill Agent)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL_ID=llama-3.3-70b-versatile

# Google Gemini (Packaging Photo Multimodal OCR, Deep Agent)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_ID=gemini-2.5-flash

# Amazon Cognito
COGNITO_USER_POOL_ID=your_cognito_user_pool_id
COGNITO_APP_CLIENT_ID=your_cognito_app_client_id
```
