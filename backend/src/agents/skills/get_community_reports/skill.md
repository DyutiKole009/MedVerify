---
name: get-community-reports
description: >-
  Retrieve crowd-sourced issue reports, adverse reactions, and suspected counterfeit flags
  submitted against a batch or drug from DynamoDB. Use to check real-world signals.
---

# Skill: get_community_reports

The `get_community_reports` skill queries user-submitted real-world reports (e.g. side effects, packaging defects, suspected counterfeits) indexed in DynamoDB, reporting active community signals separate from official regulatory notices.

---

## 1. Tool Metadata

| Property | Value |
|---|---|
| **Function Name** | `get_community_reports` |
| **Module** | `backend/src/tools/skill_tools.py` |
| **Execution Tier** | Tier 1 (Skill Agent) |
| **Underlying Store** | Amazon DynamoDB (`MedVerify_Reports` GSI1 & GSI2) |
| **Average Latency** | < 30 ms |

---

## 2. Input Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `batch_no` | `Optional[str]` | Conditional | Batch number to query GSI1 (`BATCH#<batch_no>`). |
| `drug_name` | `Optional[str]` | Conditional | Drug name to query GSI2 (`DRUG#<drug_name>`). |

*Note: At least one of `batch_no` or `drug_name` must be provided.*

---

## 3. Execution Procedure

1. **GSI Routing**:
   - If `batch_no` is present: queries `GSI1` with `KeyConditionExpression=Key("GSI1PK").eq(f"BATCH#{batch_no}")`.
   - Else if `drug_name` is present: queries `GSI2` with `KeyConditionExpression=Key("GSI2PK").eq(f"DRUG#{drug_name.lower().strip()}")`.
   - Limits results to 50 items.
2. **Community Flag Determination**:
   Sets `community_flag = True` if any retrieved report has `status == "APPROVED"`.
3. **Response Format**:
   ```python
   {
       "report_count": int,
       "reports": list[dict],
       "community_flag": bool
   }
   ```

---

## 4. Architectural Non-Negotiable: Separation of Signals

> Community reports represent crowd-sourced, real-world user feedback.
> Under MedVerify design principle §1.2, **community signals and official CDSCO alerts must never be merged into a single verdict or score**. They must be presented side-by-side as separate sources.

---

## 5. Python Example

```python
from src.tools.skill_tools import get_community_reports

community_data = get_community_reports(batch_no="B-9021")
print(f"Total Reports: {community_data['report_count']}")
print(f"Community Flagged: {community_data['community_flag']}")
for report in community_data["reports"]:
    print(f"- [{report.get('issue_type')}] {report.get('description')}")
```
