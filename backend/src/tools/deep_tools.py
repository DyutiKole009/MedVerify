"""Dynamic investigation tools used by the Deep Agent."""
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from src.config import settings
from src.tools.aws import get_bedrock_agent_runtime_client, get_agentcore_client
from src.tools.skill_tools import check_batch as skill_check_batch
from src.tools.skill_tools import get_case_history as skill_get_case_history
from src.tools.skill_tools import get_community_reports as skill_get_community_reports
from src.tools.skill_tools import get_manufacturer_history as skill_get_manufacturer_history
from src.tools.skill_tools import get_notice as skill_get_notice
from src.tools.skill_tools import search_drug as skill_search_drug


@tool
def check_batch(batch_no: str, drug_name: Optional[str] = None, manufacturer: Optional[str] = None) -> Dict[str, Any]:
    """Check official evidence for a medicine batch."""
    return skill_check_batch(batch_no, drug_name, manufacturer)


@tool
def get_manufacturer_history(manufacturer_name: str) -> Dict[str, Any]:
    """Retrieve official manufacturer history."""
    return skill_get_manufacturer_history(manufacturer_name)


@tool
def get_community_reports(batch_no: Optional[str] = None, drug_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve community reports for a batch or drug."""
    return skill_get_community_reports(batch_no, drug_name)


@tool
def get_notice(source_document_s3_key: str) -> Dict[str, Any]:
    """Fetch a regulatory notice."""
    return skill_get_notice(source_document_s3_key)


@tool
def get_case_history(session_id: str) -> Dict[str, Any]:
    """Retrieve a prior investigation session as context."""
    return skill_get_case_history(session_id)


@tool
def search_drug(fuzzy_text: str, size: int = 5) -> Dict[str, Any]:
    """Search for likely drug and manufacturer matches."""
    return skill_search_drug(fuzzy_text, size)


@tool
def retrieve_related_notices(query_text: str, number_of_results: int = 5) -> Dict[str, Any]:
    """Retrieve regulatory notice excerpts related to the current case from Bedrock Knowledge Base."""
    client = get_bedrock_agent_runtime_client()
    response = client.retrieve(
        knowledgeBaseId=settings.BEDROCK_KB_ID,
        retrievalQuery={"text": query_text},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": number_of_results
            }
        }
    )
    results = [
        {
            "content": item.get("content", {}).get("text", ""),
            "s3_uri": item.get("location", {}).get("s3Location", {}).get("uri", ""),
            "score": item.get("score", 0.0),
        }
        for item in response.get("retrievalResults", [])
    ]
    return {"results": results}


@tool
def retrieve_similar_cases(query_text: str, actor_id: str = "anonymous") -> Dict[str, Any]:
    """Retrieve prior case context without treating it as current evidence from AgentCore Memory."""
    namespace = "manufacturer-patterns" if actor_id == "shared" else f"user/{actor_id}"
    client = get_agentcore_client()
    response = client.retrieve_memory_records(
        memoryId=settings.AGENTCORE_MEMORY_ID,
        namespace=namespace,
        searchCriteria={"query": query_text},
        maxResults=5,
    )
    return {"records": response.get("memoryRecords", [])}


@tool
def record_investigation_event(actor_id: str, session_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Record a Deep Agent step in short-term AgentCore Memory."""
    client = get_agentcore_client()
    response = client.create_event(
        memoryId=settings.AGENTCORE_MEMORY_ID,
        actorId=actor_id,
        sessionId=session_id,
        messages=messages,
    )
    return response


DEEP_TOOLS = [
    check_batch,
    get_manufacturer_history,
    get_community_reports,
    get_notice,
    get_case_history,
    search_drug,
    retrieve_related_notices,
    retrieve_similar_cases,
    record_investigation_event,
]