"""
Feedback-Gated RAG Improvement loop (§6.4).
Promotes validated, high-quality investigation sessions with positive user feedback into the Bedrock Knowledge Base.
"""
import json
from typing import Dict, Any, List
from boto3.dynamodb.conditions import Attr

from src.tools.aws import get_dynamodb_resource, get_s3_client, get_boto_session
from src.config import settings
from src.utils.logger import logger


def promote_feedback_sessions_to_kb(limit: int = 20) -> int:
    """
    Scans for sessions meeting:
      - feedback.helpful == True
      - promoted_to_kb != True
    Strips PII and publishes sanitized narrative to the case-history corpus.
    """
    dynamo = get_dynamodb_resource()
    sessions_table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
    s3 = get_s3_client()

    # Scan for eligible sessions
    scan_res = sessions_table.scan(
        FilterExpression=Attr("feedback.helpful").eq(True) & (Attr("promoted_to_kb").not_exists() | Attr("promoted_to_kb").eq(False)),
        Limit=limit,
    )
    eligible_sessions: List[Dict[str, Any]] = scan_res.get("Items", [])
    promoted_count = 0

    for session in eligible_sessions:
        session_id = session.get("PK", "").replace("SESSION#", "")
        if not session_id:
            continue

        input_data = session.get("input_data", {})
        final_result = session.get("final_result", {})

        drug_name = input_data.get("drug_name") or "Unknown Drug"
        batch_no = input_data.get("batch_no") or "Unknown Batch"
        manufacturer = input_data.get("manufacturer") or "Unknown Manufacturer"
        explanation = final_result.get("explanation_text") or final_result.get("explanation") or str(final_result)

        # Sanitize PII: No user_id, no raw customer image URLs
        sanitized_narrative = (
            f"Case History - Drug: {drug_name}\n"
            f"Batch: {batch_no}\n"
            f"Manufacturer: {manufacturer}\n"
            f"Mode: {session.get('mode', 'INVESTIGATION')}\n\n"
            f"Investigation Finding:\n{explanation}\n"
        )

        metadata_sidecar = {
            "metadataAttributes": {
                "source_type": "case_history",
                "drug_name": str(drug_name).lower(),
                "batch_no": str(batch_no).upper(),
                "manufacturer_name": str(manufacturer).lower(),
                "session_id": session_id,
            }
        }

        # Write text document and metadata sidecar to S3 KB case-history bucket
        s3_doc_key = f"case-history/{session_id}.txt"
        s3_meta_key = f"case-history/{session_id}.txt.metadata.json"

        s3.put_object(
            Bucket=settings.S3_KB_DOCUMENTS_BUCKET,
            Key=s3_doc_key,
            Body=sanitized_narrative.encode("utf-8"),
            ContentType="text/plain",
        )
        s3.put_object(
            Bucket=settings.S3_KB_DOCUMENTS_BUCKET,
            Key=s3_meta_key,
            Body=json.dumps(metadata_sidecar).encode("utf-8"),
            ContentType="application/json",
        )

        # Mark session as promoted in DynamoDB
        sessions_table.update_item(
            Key={"PK": session["PK"], "SK": session.get("SK", "META")},
            UpdateExpression="SET promoted_to_kb = :p",
            ExpressionAttributeValues={":p": True},
        )

        promoted_count += 1
        logger.info(f"Promoted session {session_id} to Bedrock KB case history.")

    # Trigger Bedrock Knowledge Base sync if items were promoted
    if promoted_count > 0 and settings.BEDROCK_KB_ID and settings.BEDROCK_KB_DATA_SOURCE_CASES_ID:
        try:
            agent_client = get_boto_session().client("bedrock-agent")
            agent_client.start_ingestion_job(
                knowledgeBaseId=settings.BEDROCK_KB_ID,
                dataSourceId=settings.BEDROCK_KB_DATA_SOURCE_CASES_ID,
                description=f"Automated sync: {promoted_count} feedback-promoted cases",
            )
            logger.info("Triggered Bedrock Knowledge Base ingestion job.")
        except Exception as exc:
            logger.warning(f"Bedrock KB ingestion job trigger skipped: {exc}")

    return promoted_count
