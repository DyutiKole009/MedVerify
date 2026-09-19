import pytest
from moto import mock_aws
import boto3
from src.aws_wrappers.eventbridge import EventBridgeWrapper
from src.aws_wrappers.client_factory import clear_client_cache

@pytest.fixture(autouse=True)
def setup_eventbridge():
    with mock_aws():
        clear_client_cache()
        client = boto3.client("events", region_name="us-east-1")
        # default bus exists in AWS by default
        yield

def test_put_event():
    wrapper = EventBridgeWrapper()
    res = wrapper.put_event(
        source="medverify.ingestion",
        detail_type="NSQAlertIngested",
        detail={"batch_no": "B999", "status": "NSQ"}
    )
    assert res.get("FailedEntryCount") == 0
    assert len(res.get("Entries", [])) == 1

def test_put_batch_events():
    wrapper = EventBridgeWrapper()
    entries = [
        {"source": "medverify.ingestion", "detail_type": "DocParsed", "detail": {"doc_id": "1"}},
        {"source": "medverify.ingestion", "detail_type": "DocParsed", "detail": {"doc_id": "2"}}
    ]
    res = wrapper.put_batch_events(entries)
    assert res.get("FailedEntryCount") == 0
    assert len(res.get("Entries", [])) == 2
