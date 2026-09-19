---
name: check-batch
description: >-
  Lookup official CDSCO regulatory quality records (NSQ or spurious alerts) and community
  status for a medicine batch from DynamoDB. Use whenever verifying a specific batch number.
---

# Skill: check_batch

The `check_batch` skill is a deterministic single-step lookup tool used by the Skill Agent to query the official regulatory status and community flags for a specific drug batch.

---

## 1. Tool Metadata

| Property | Value |
|---|---|
| **Function Name** | `check_batch` |
| **Module** | `backend/src/tools/skill_tools.py` |
| **Execution Tier** | Tier 1 (Skill Agent) |
| **Underlying Store** | Amazon DynamoDB (`MedVerify_Batches`) |
| **Average Latency** | < 20 ms |

---

## 2. Input Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `batch_no` | `str` | Yes | The batch number (e.g. `"B-9021"`, `"NX102"`). |
| `drug_name` | `str` | No | Normalized drug name for cross-validation. |
| `manufacturer` | `str` | No | Manufacturer name to pinpoint exact (batch, manufacturer) pair. |

---

## 3. Execution Procedure

1. **Normalization**:
   Before querying, clean the batch number using `src.domain.normalization.normalize_batch_no`.
2. **Key Construction**:
   - `PK`: `BATCH#{batch_no}`
   - `SK`: `MFR#{manufacturer_id}` (if manufacturer is specified).
3. **DynamoDB Operation**:
   - If `manufacturer` is provided: executes a point `get_item(Key={"PK": ..., "SK": ...})`.
   - If `manufacturer` is omitted: executes a `query(KeyConditionExpression=Key("PK").eq(...))` returning up to 10 matching records.
4. **Validation**:
   - If `drug_name` is provided, verifies `record.drug_name_normalized == drug_name.lower().strip()`.
5. **Response Format**:
   ```python
   {
       "found": bool,
       "batch_record": dict | None,
       "community_flag": bool
   }
   ```

---

## 4. Key Return Fields

When `found` is `True`, `batch_record` contains:
- `batch_no`: Printed batch number.
- `drug_name`: Drug name as recorded in the alert.
- `manufacturer_name`: Name and address of manufacturer.
- `alert_status`: `NONE` | `NSQ` | `SPURIOUS`.
- `nsq_reason`: Reason for failure (e.g. "Fails dissolution test", "Assay").
- `source_month`: Month of CDSCO alert publication (`YYYY-MM`).
- `community_flag`: Boolean indicating whether community issue reports have been validated.

---

## 5. Non-Negotiable Compliance Rule

> **Absence of a flag is not proof of safety.**
> If `found` is `False`, the caller must NOT assert the medicine is safe or genuine. It simply means no regulatory alert has been indexed for this batch.

---

## 6. Python Example

```python
from src.tools.skill_tools import check_batch

result = check_batch(batch_no="B-9021", manufacturer="Acme Pharma Ltd")
if result["found"]:
    record = result["batch_record"]
    print(f"Alert Status: {record['alert_status']}")
    print(f"Reason: {record.get('nsq_reason')}")
else:
    print("No regulatory record found for this batch.")
```
