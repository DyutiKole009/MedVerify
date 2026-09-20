---
name: get-case-history
description: >-
  Retrieve a previously stored medicine verification session, reasoning trajectory, and
  feedback record by session ID from DynamoDB. Use when inspecting prior check outcomes.
---

# Skill: get_case_history

The `get_case_history` skill retrieves past investigation session records from DynamoDB, allowing users or investigative agents to review previous verification conclusions, evidence traces, and user feedback.

---

## 1. Tool Metadata

| Property | Value |
|---|---|
| **Function Name** | `get_case_history` |
| **Module** | `backend/src/tools/skill_tools.py` |
| **Execution Tier** | Tier 1 (Skill Agent) |
| **Underlying Store** | Amazon DynamoDB (`MedVerify_Sessions`) |
| **Average Latency** | < 25 ms |

---

## 2. Input Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `session_id` | `str` | Yes | The session UUID (e.g. `"8f03c0b2-4d29-4d6b-9c7a-9a9446f25dc1"`). |

---

## 3. Execution Procedure

1. **Direct Point Query**:
   Executes `get_item` on `MedVerify_Sessions` table:
   - `PK`: `SESSION#{session_id}`
   - `SK`: `RESULT`
2. **Decimal Conversion**:
   Converts any DynamoDB `Decimal` numeric types to standard Python primitives via `convert_decimals_to_primitives`.
3. **Response Format**:
   ```python
   {
       "session_record": dict | None
   }
   ```

---

## 4. Key Session Record Fields

When found, `session_record` contains:
- `session_id`: Unique identifier.
- `tier`: The agent tier that handled the check (`SKILL`, `REACTIVE`, `DEEP`).
- `status_category`: Verification result category (`CLEAR`, `NSQ`, `SPURIOUS`, `COMMUNITY_FLAGGED`, `NO_MATCH`).
- `summary`: Explanation generated for the user.
- `evidence`: Detailed evidence map (batches, manufacturer info, reports).
- `feedback`: Recorded user feedback (`{"helpful": bool, "comment": str, "timestamp": str}`).
- `promoted_to_kb`: Boolean flag indicating if promoted to Knowledge Base.

---

## 5. Python Example

```python
from src.tools.skill_tools import get_case_history

history = get_case_history("8f03c0b2-4d29-4d6b-9c7a-9a9446f25dc1")
if history["session_record"]:
    session = history["session_record"]
    print("Handled by Tier:", session.get("tier"))
    print("Outcome:", session.get("status_category"))
    print("Summary:", session.get("summary"))
```
