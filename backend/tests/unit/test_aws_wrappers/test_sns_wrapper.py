import pytest
from moto import mock_aws
import boto3
from src.aws_wrappers.sns import SNSWrapper
from src.aws_wrappers.client_factory import clear_client_cache

@pytest.fixture(autouse=True)
def setup_sns():
    with mock_aws():
        clear_client_cache()
        client = boto3.client("sns", region_name="us-east-1")
        topic = client.create_topic(Name="medverify-spurious-alerts")
        yield topic["TopicArn"]

def test_publish_alert(setup_sns):
    topic_arn = setup_sns
    wrapper = SNSWrapper()
    msg_id = wrapper.publish_alert(
        subject="Test Alert",
        message="This is a test notification",
        topic_arn=topic_arn
    )
    assert msg_id is not None
    assert len(msg_id) > 0

def test_publish_spurious_alert(setup_sns):
    topic_arn = setup_sns
    wrapper = SNSWrapper()
    msg_id = wrapper.publish_spurious_medicine_alert(
        batch_no="SPUR101",
        drug_name="FakeCillin 500mg",
        manufacturer="Non-existent Laboratories",
        reason="Fictitious manufacturer identified"
    )
    assert msg_id is not None
