---
name: get-manufacturer-history
description: >-
  Retrieve the risk profile, aggregate flag counts, and recent 20 flagged batches for a
  pharmaceutical manufacturer from DynamoDB. Use when assessing manufacturer track record.
---

# Skill: get_manufacturer_history

The `get_manufacturer_history` skill queries a manufacturer's historical compliance record from DynamoDB, including aggregate counts of NSQ and spurious drug alerts, and retrieves their recent flagged batches.

---

## 1. Tool Metadata

| Property | Value |
|---|---|
| **Function Name** | `get_manufacturer_history` |
| **Module** | `backend/src/tools/skill_tools.py` |
| **Execution Tier** | Tier 1 (Skill Agent) |
| **Underlying Store** | Amazon DynamoDB (`MedVerify_Manufacturers` & `MedVerify_Batches` GSI2) |
| **Average Latency** | < 35 ms |

---

## 2. Input Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `manufacturer_name` | `str` | Yes | The manufacturer name (e.g. `"Acme Pharma Ltd"`, `"Sun Pharma"`). |

---

## 3. Execution Procedure

1. **Identifier Resolution**:
   Normalizes the manufacturer name into an uppercase key with hash separators (`ACME#PHARMA#LTD`).
2. **Profile Fetch**:
   Executes `get_item(Key={"PK": f"MFR#{manufacturer_id}"})` against the `MedVerify_Manufacturers` table.
3. **Recent Batches Fetch**:
   Queries `GSI2` on `MedVerify_Batches`:
   - `GSI2PK`: `MFR#{manufacturer_id}`
   - `GSI2SK`: `begins_with("BATCH#")`
   - Ordered descending (`ScanIndexForward=False`) with a limit of 20.
4. **Response Format**:
   ```python
   {
       "manufacturer_record": dict | None,
       "recent_batches": list[dict]
   }
   ```

---

## 4. Key Return Fields

When found, `manufacturer_record` includes:
- `manufacturer_name`: Display name.
- `total_flags`: Total count of NSQ batches ever published for this manufacturer.
- `spurious_count`: Number of batches flagged specifically as counterfeit or spurious.
- `last_flagged_date`: Timestamp of the most recent alert (`YYYY-MM-DD`).

`recent_batches` contains up to 20 batch summaries:
- `batch_no`, `drug_name`, `alert_status`, `nsq_reason`, `source_month`.

---

## 5. Python Example

```python
from src.tools.skill_tools import get_manufacturer_history

history = get_manufacturer_history("Acme Pharma Ltd")
if history["manufacturer_record"]:
    rec = history["manufacturer_record"]
    print(f"Total Flags: {rec.get('total_flags', 0)}")
    print(f"Spurious Flags: {rec.get('spurious_count', 0)}")
    print(f"Recent Flagged Batches: {len(history['recent_batches'])}")
```
