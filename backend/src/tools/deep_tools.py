"""Dynamic investigation tools used by the Deep Agent (LangGraph + Gemini)."""
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from src.config import settings
from src.tools.aws import opensearch_search
from src.tools.skill_tools import check_batch as skill_check_batch
from src.tools.skill_tools import get_case_history as skill_get_case_history
from src.tools.skill_tools import get_community_reports as skill_get_community_reports
from src.tools.skill_tools import get_manufacturer_history as skill_get_manufacturer_history
from src.tools.skill_tools import get_notice as skill_get_notice
from src.tools.skill_tools import search_drug as skill_search_drug
from src.tools.skill_tools import retrieve_regulatory_advisory as skill_retrieve_regulatory_advisory



@tool
def check_batch(batch_no: str, drug_name: Optional[str] = None, manufacturer: Optional[str] = None) -> Dict[str, Any]:
    """Check official CDSCO evidence for a medicine batch."""
    return skill_check_batch(batch_no, drug_name, manufacturer)


@tool
def get_manufacturer_history(manufacturer_name: str) -> Dict[str, Any]:
    """Retrieve official manufacturer history and risk profile."""
    return skill_get_manufacturer_history(manufacturer_name)


@tool
def get_community_reports(batch_no: Optional[str] = None, drug_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve community reports for a batch or drug."""
    return skill_get_community_reports(batch_no, drug_name)


@tool
def get_notice(source_document_s3_key: str) -> Dict[str, Any]:
    """Fetch the full text of a regulatory notice from S3."""
    return skill_get_notice(source_document_s3_key)


@tool
def get_case_history(session_id: str) -> Dict[str, Any]:
    """Retrieve a prior investigation session as context."""
    return skill_get_case_history(session_id)


@tool
def search_drug(fuzzy_text: str, size: int = 5) -> Dict[str, Any]:
    """Fuzzy-search drug names, manufacturers, and batches in OpenSearch."""
    return skill_search_drug(fuzzy_text, size)


@tool
def retrieve_related_notices(query_text: str, number_of_results: int = 5) -> Dict[str, Any]:
    """
    Retrieve regulatory notice excerpts related to the current case.
    Searches the OpenSearch drug index for matching alert text.
    """
    try:
        query = {
            "size": number_of_results,
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["search_text^2", "drug_name", "manufacturer_name"],
                    "fuzziness": "AUTO",
                }
            },
        }
        hits = opensearch_search(settings.OPENSEARCH_INDEX_DRUGS, query)
        results = [
            {
                "content": item.get("_source", {}).get("search_text", ""),
                "s3_uri": item.get("_source", {}).get("s3_uri", ""),
                "score": item.get("_score", 0.0),
            }
            for item in hits
        ]
        return {"results": results}
    except Exception:
        return {"results": []}


@tool
def retrieve_similar_cases(
    batch_no: Optional[str] = None,
    drug_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve prior community cases from DynamoDB reports."""
    return skill_get_community_reports(batch_no=batch_no, drug_name=drug_name)


@tool
def retrieve_regulatory_advisory(query_text: str, number_of_results: int = 3) -> Dict[str, Any]:
    """
    Retrieve qualitative CDSCO regulatory advisories, packaging inspection standards,
    transit theft alerts, clinical failure monographs, or patient safety SOPs
    from the Amazon Bedrock Knowledge Base.
    """
    return skill_retrieve_regulatory_advisory(query_text=query_text, number_of_results=number_of_results)


DEEP_TOOLS = [
    check_batch,
    get_manufacturer_history,
    get_community_reports,
    get_notice,
    get_case_history,
    search_drug,
    retrieve_related_notices,
    retrieve_similar_cases,
    retrieve_regulatory_advisory,
]

