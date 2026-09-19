---
name: get-notice
description: >-
  Fetch stored raw CDSCO regulatory notice text or alert documents from the S3 raw-documents
  bucket. Use when full official notice text or citations are required.
---

# Skill: get_notice

The `get_notice` skill retrieves raw regulatory alert text and official documentation from the MedVerify S3 raw document repository, supplying complete text evidence and traceable citations.

---

## 1. Tool Metadata

| Property | Value |
|---|---|
| **Function Name** | `get_notice` |
| **Module** | `backend/src/tools/skill_tools.py` |
| **Execution Tier** | Tier 1 (Skill Agent) |
| **Underlying Store** | Amazon S3 (`settings.S3_RAW_DOCUMENTS_BUCKET`) |
| **Average Latency** | < 100 ms |

---

## 2. Input Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `source_document_s3_key` | `str` | Yes | The S3 object key (e.g. `"notices/2024-05-alert-paracetamol.txt"`). |

---

## 3. Execution Procedure

1. **Client Acquisition**:
   Acquires standard `boto3` S3 client configured via `src.tools.aws.get_s3_client()`.
2. **Object Retrieval**:
   Calls `s3.get_object(Bucket=settings.S3_RAW_DOCUMENTS_BUCKET, Key=source_document_s3_key)`.
3. **Decoding**:
   Reads the object body and safely decodes to a UTF-8 string (replacing non-decodable bytes).
4. **Citation Generation**:
   Generates a canonical S3 URI (`s3://<bucket>/<key>`) for provenance tracking.
5. **Response Format**:
   ```python
   {
       "notice_text": str,
       "source_url": str
   }
   ```

---

## 4. Python Example

```python
from src.tools.skill_tools import get_notice

notice = get_notice("notices/cdsco-nsq-2024-05.txt")
print("Citation:", notice["source_url"])
print("Notice Snippet:", notice["notice_text"][:200])
```
