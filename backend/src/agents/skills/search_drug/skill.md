---
name: search-drug
description: >-
  Fuzzy-search drug names, manufacturers, and batches in Amazon OpenSearch to resolve OCR
  misspellings, partial brand names, or consumer typos.
---

# Skill: search_drug

The `search_drug` skill performs approximate fuzzy text search across the `medverify-drugs` OpenSearch index to resolve misspelled brand names, phonetic OCR errors, and partial medicine names.

---

## 1. Tool Metadata

| Property | Value |
|---|---|
| **Function Name** | `search_drug` |
| **Module** | `backend/src/tools/skill_tools.py` |
| **Execution Tier** | Tier 1 (Skill Agent) |
| **Underlying Store** | Amazon OpenSearch Service (`settings.OPENSEARCH_INDEX_DRUGS`) |
| **Average Latency** | < 45 ms |

---

## 2. Input Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `fuzzy_text` | `str` | Yes | Search query or misspelled term (e.g. `"paracetmol"`, `"crocin 650"`). |
| `size` | `int` | No | Max candidate matches to return (default: `5`). |

---

## 3. Execution Procedure

1. **Query Construction**:
   Builds an OpenSearch fuzzy DSL query:
   ```json
   {
       "size": size,
       "query": {
           "fuzzy": {
               "search_text": {
                   "value": fuzzy_text,
                   "fuzziness": "AUTO",
                   "prefix_length": 1
               }
           }
       }
   }
   ```
2. **SigV4 Authentication & Execution**:
   Calls `src.tools.aws.opensearch_search()` which automatically signs HTTP requests with AWS SigV4 for OpenSearch.
3. **Response Format**:
   ```python
   {
       "candidates": [
           {
               "drug_name": str,
               "manufacturer": str,
               "batch_no": str,
               "score": float
           }
       ]
   }
   ```

---

## 4. Python Example

```python
from src.tools.skill_tools import search_drug

matches = search_drug("paracetmol", size=3)
for candidate in matches["candidates"]:
    print(f"Match: {candidate['drug_name']} ({candidate['manufacturer']}) - Score: {candidate['score']}")
```
