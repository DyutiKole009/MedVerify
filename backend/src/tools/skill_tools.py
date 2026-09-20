"""Deterministic lookup tools used by the Skill Agent."""
from typing import Any, Dict, Optional

from boto3.dynamodb.conditions import Key
try:
    from strands import tool
except ImportError:
    def tool(func):
        return func

from src.config import settings
from src.domain.normalization import normalize_batch_no, build_manufacturer_id
from src.tools.aws import (
    get_dynamodb_resource,
    get_s3_client,
    convert_decimals_to_primitives,
    opensearch_search,
)


@tool
def check_batch(batch_no: str, drug_name: Optional[str] = None, manufacturer: Optional[str] = None) -> Dict[str, Any]:
    """Look up an official batch record and return its community status."""
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_BATCHES_TABLE)

    norm_batch = normalize_batch_no(batch_no)
    batches_to_try = [norm_batch]
    if batch_no and batch_no.strip() not in batches_to_try:
        batches_to_try.append(batch_no.strip())
    if batch_no and batch_no.strip().upper() not in batches_to_try:
        batches_to_try.append(batch_no.strip().upper())

    record = None
    for b in batches_to_try:
        if manufacturer:
            mfr_id = build_manufacturer_id(manufacturer)
            response = table.get_item(Key={"PK": f"BATCH#{b}", "SK": f"MFR#{mfr_id}"})
            if response.get("Item"):
                record = response.get("Item")
                break
        
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"BATCH#{b}"),
            Limit=10,
        )
        items = response.get("Items", [])
        if items:
            record = items[0]
            break

    if not record:
        return {"found": False, "batch_record": None, "community_flag": False}

    record = convert_decimals_to_primitives(record)
    
    # Fuzzy/token containment match for drug name to avoid false negatives on dosage/salt variants
    if drug_name and record.get("drug_name_normalized"):
        u_drug = drug_name.lower().strip()
        r_drug = record["drug_name_normalized"].lower().strip()
        if u_drug not in r_drug and r_drug not in u_drug:
            u_tokens = set(u_drug.split())
            r_tokens = set(r_drug.split())
            if not (u_tokens & r_tokens):
                return {"found": False, "batch_record": None, "community_flag": False}

    return {"found": True, "batch_record": record, "community_flag": bool(record.get("community_flag", False))}


@tool
def get_manufacturer_history(manufacturer_name: str) -> Dict[str, Any]:
    """Return the manufacturer record and recent batches from GSI2."""
    dynamo = get_dynamodb_resource()
    mfr_table = dynamo.Table(settings.DYNAMODB_MANUFACTURERS_TABLE)
    batches_table = dynamo.Table(settings.DYNAMODB_BATCHES_TABLE)

    mfr_token = manufacturer_name.strip().upper().split()[0] if manufacturer_name.strip() else ""
    mfr_id = build_manufacturer_id(manufacturer_name)
    mfr_res = mfr_table.get_item(Key={"PK": f"MFR#{mfr_id}"})
    manufacturer = convert_decimals_to_primitives(mfr_res.get("Item")) if mfr_res.get("Item") else None

    # If exact ID not found, scan for partial match on manufacturer name
    if not manufacturer and mfr_token:
        try:
            scan_res = mfr_table.scan(
                FilterExpression="contains(PK, :tok)",
                ExpressionAttributeValues={":tok": mfr_token},
                Limit=5
            )
            items = scan_res.get("Items", [])
            if items:
                manufacturer = convert_decimals_to_primitives(items[0])
                mfr_id = manufacturer.get("PK", "").replace("MFR#", "")
        except Exception:
            pass

    batches = []
    if mfr_id:
        try:
            batches_res = batches_table.query(
                IndexName="GSI2",
                KeyConditionExpression=Key("GSI2PK").eq(f"MFR#{mfr_id}") & Key("GSI2SK").begins_with("BATCH#"),
                Limit=20,
                ScanIndexForward=False,
            )
            batches = [convert_decimals_to_primitives(item) for item in batches_res.get("Items", [])]
        except Exception:
            pass

    if not batches and mfr_token:
        try:
            batch_scan = batches_table.scan(
                FilterExpression="contains(GSI2PK, :tok)",
                ExpressionAttributeValues={":tok": mfr_token},
                Limit=20
            )
            batches = [convert_decimals_to_primitives(item) for item in batch_scan.get("Items", [])]
        except Exception:
            pass

    return {"manufacturer_record": manufacturer, "recent_batches": batches}


@tool
def get_notice(source_document_s3_key: str) -> Dict[str, Any]:
    """Fetch a stored regulatory notice from the raw-document bucket."""
    s3 = get_s3_client()
    response = s3.get_object(Bucket=settings.S3_RAW_DOCUMENTS_BUCKET, Key=source_document_s3_key)
    body = response["Body"].read()
    return {
        "notice_text": body.decode("utf-8", errors="replace"),
        "source_url": f"s3://{settings.S3_RAW_DOCUMENTS_BUCKET}/{source_document_s3_key}",
    }


@tool
def get_case_history(session_id: str) -> Dict[str, Any]:
    """Retrieve a previously stored investigation session."""
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
    res = table.get_item(Key={"PK": f"SESSION#{session_id}", "SK": "RESULT"})
    session_record = convert_decimals_to_primitives(res.get("Item")) if res.get("Item") else None
    return {"session_record": session_record}


@tool
def get_community_reports(batch_no: Optional[str] = None, drug_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve community reports by batch or drug GSI."""
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(settings.DYNAMODB_REPORTS_TABLE)

    if batch_no:
        res = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(f"BATCH#{batch_no}"),
            Limit=50,
        )
        reports = [convert_decimals_to_primitives(i) for i in res.get("Items", [])]
    elif drug_name:
        res = table.query(
            IndexName="GSI2",
            KeyConditionExpression=Key("GSI2PK").eq(f"DRUG#{drug_name.lower().strip()}"),
            Limit=50,
        )
        reports = [convert_decimals_to_primitives(i) for i in res.get("Items", [])]
    else:
        return {"report_count": 0, "reports": [], "community_flag": False}

    return {
        "report_count": len(reports),
        "reports": reports,
        "community_flag": any(report.get("status") == "APPROVED" for report in reports),
    }


@tool
def search_drug(fuzzy_text: str, size: int = 5) -> Dict[str, Any]:
    """Find likely drug, manufacturer, and batch matches across OpenSearch and DynamoDB."""
    candidates = []
    
    # 1. Attempt OpenSearch search with multi-match
    try:
        query = {
            "size": size,
            "query": {
                "multi_match": {
                    "query": fuzzy_text,
                    "fields": ["drug_name^2", "search_text", "manufacturer_name", "batch_no"],
                    "fuzziness": "AUTO",
                }
            },
        }
        hits = opensearch_search(settings.OPENSEARCH_INDEX_DRUGS, query)
        for hit in hits:
            candidates.append({
                "drug_name": hit.get("_source", {}).get("drug_name"),
                "manufacturer": hit.get("_source", {}).get("manufacturer_name"),
                "batch_no": hit.get("_source", {}).get("batch_no"),
                "alert_status": hit.get("_source", {}).get("alert_status", "UNKNOWN"),
                "nsq_reason": hit.get("_source", {}).get("nsq_reason", ""),
                "score": hit.get("_score", 0.0),
            })
    except Exception:
        pass

    # 2. Resilient DynamoDB fallback if OpenSearch returned no candidates
    if not candidates and fuzzy_text:
        try:
            dynamo = get_dynamodb_resource()
            batches_table = dynamo.Table(settings.DYNAMODB_BATCHES_TABLE)
            clean_term = fuzzy_text.lower().strip()
            
            # Scan with filter on normalized drug or batch
            scan_res = batches_table.scan(
                FilterExpression="contains(drug_name_normalized, :t) OR contains(batch_no_normalized, :tb)",
                ExpressionAttributeValues={
                    ":t": clean_term,
                    ":tb": clean_term.upper(),
                },
                Limit=size,
            )
            for item in scan_res.get("Items", []):
                clean_item = convert_decimals_to_primitives(item)
                candidates.append({
                    "drug_name": clean_item.get("drug_name"),
                    "manufacturer": clean_item.get("manufacturer_name"),
                    "batch_no": clean_item.get("batch_no"),
                    "alert_status": clean_item.get("alert_status", "CLEAR"),
                    "nsq_reason": clean_item.get("nsq_reason", ""),
                    "score": 1.0,
                })
        except Exception:
            pass

    return {"candidates": candidates}


@tool
def retrieve_regulatory_advisory(query_text: str, number_of_results: int = 4) -> Dict[str, Any]:
    """
    Retrieve qualitative regulatory advisories, packaging inspection standards,
    transit theft alerts, clinical failure monographs, or patient safety SOPs
    from the Amazon Bedrock Knowledge Base.
    """
    try:
        from src.tools.aws import get_boto_session
        runtime = get_boto_session().client("bedrock-agent-runtime")
        kb_id = "W7Q20DERIH"
        resp = runtime.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query_text},
        )

        results = []
        for item in resp.get("retrievalResults", []):
            content = item.get("content", {}).get("text", "")
            s3_uri = item.get("location", {}).get("s3Location", {}).get("uri", "")
            score = item.get("score", 0.0)
            results.append({
                "content": content,
                "s3_uri": s3_uri,
                "score": score
            })
        return {"found": True, "results": results}
    except Exception as exc:
        return {"found": False, "results": [], "error": str(exc)}


SKILL_TOOLS = [check_batch, get_manufacturer_history, get_notice, get_case_history, get_community_reports, search_drug, retrieve_regulatory_advisory]