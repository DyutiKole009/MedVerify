"""
Amazon EventBridge wrapper for publishing domain events and triggering background pipelines.
"""
from typing import Dict, Any, List, Optional
import json
from src.aws_wrappers.base import BaseAWSWrapper, catch_aws_errors
from src.aws_wrappers.client_factory import get_boto_client
from src.config import settings
from src.utils.logger import logger

class EventBridgeWrapper(BaseAWSWrapper):
    """Encapsulates EventBridge event publishing for ingestion and background events."""
    def __init__(self):
        super().__init__("EventBridge")
        self.client = get_boto_client("events")

    @catch_aws_errors("PutEvents")
    def put_event(
        self,
        source: str,
        detail_type: str,
        detail: Dict[str, Any],
        event_bus_name: Optional[str] = None,
        resources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Publishes a single event to the EventBridge bus."""
        entry: Dict[str, Any] = {
            "Source": source,
            "DetailType": detail_type,
            "Detail": json.dumps(detail),
            "EventBusName": event_bus_name or settings.EVENT_BUS_NAME
        }
        if resources:
            entry["Resources"] = resources

        response = self.client.put_events(Entries=[entry])
        failed_count = response.get("FailedEntryCount", 0)
        if failed_count > 0:
            logger.error(f"Failed to publish event to EventBridge: {response.get('Entries')}")
        return response

    @catch_aws_errors("PutBatchEvents")
    def put_batch_events(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Publishes a batch of events (up to 10 per request)."""
        formatted_entries = []
        for e in entries:
            entry = {
                "Source": e["source"],
                "DetailType": e["detail_type"],
                "Detail": json.dumps(e["detail"]) if isinstance(e["detail"], dict) else e["detail"],
                "EventBusName": e.get("event_bus_name", settings.EVENT_BUS_NAME)
            }
            if "resources" in e:
                entry["Resources"] = e["resources"]
            formatted_entries.append(entry)

        return self.client.put_events(Entries=formatted_entries)
