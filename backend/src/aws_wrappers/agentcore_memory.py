"""
Bedrock AgentCore Memory wrapper for short-term session events and long-term cross-session knowledge.
"""
from typing import Dict, Any, Optional, List
from src.aws_wrappers.base import BaseAWSWrapper, catch_aws_errors
from src.aws_wrappers.client_factory import get_boto_client
from src.utils.logger import logger

class AgentCoreMemoryWrapper(BaseAWSWrapper):
    """
    Encapsulates Amazon Bedrock AgentCore Memory operations (§10).
    Manages short-term reasoning events and long-term semantic pattern recall.
    """
    def __init__(self):
        super().__init__("AgentCoreMemory")
        # In AWS Bedrock, AgentCore memory is accessed through bedrock-agentcore client
        self.client = get_boto_client("bedrock-agentcore")

    @catch_aws_errors("CreateEvent")
    def create_event(
        self,
        memory_id: str,
        actor_id: str,
        session_id: str,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Records a short-term tool call or reasoning step within a Deep Agent session (§10.2).
        """
        response = self.client.create_event(
            memoryId=memory_id,
            actorId=actor_id,
            sessionId=session_id,
            messages=messages
        )
        return response

    @catch_aws_errors("ListEvents")
    def list_events(
        self,
        memory_id: str,
        actor_id: str,
        session_id: str,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Retrieves prior events within the active Deep Agent session to prevent duplicate tool execution.
        """
        response = self.client.list_events(
            memoryId=memory_id,
            actorId=actor_id,
            sessionId=session_id,
            maxResults=max_results
        )
        return response.get("events", [])

    @catch_aws_errors("GetEvent")
    def get_event(
        self,
        memory_id: str,
        actor_id: str,
        session_id: str,
        event_id: str
    ) -> Dict[str, Any]:
        """Retrieves a specific short-term event."""
        return self.client.get_event(
            memoryId=memory_id,
            actorId=actor_id,
            sessionId=session_id,
            eventId=event_id
        )

    @catch_aws_errors("RetrieveMemoryRecords")
    def retrieve_memory_records(
        self,
        memory_id: str,
        namespace: str,
        query_text: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over long-term extracted facts across sessions (§10.3).
        Common namespace: 'manufacturer-patterns' (shared global) or user-scoped.
        """
        response = self.client.retrieve_memory_records(
            memoryId=memory_id,
            namespace=namespace,
            searchCriteria={"query": query_text},
            maxResults=max_results
        )
        return response.get("memoryRecords", [])
