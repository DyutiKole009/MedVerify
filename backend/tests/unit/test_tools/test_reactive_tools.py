import pytest
from moto import mock_aws
import boto3
import json
from unittest.mock import patch, MagicMock
from src.config import settings
from src.tools.reactive_tools import (
    extract_from_image,
    normalize_and_resolve,
    run_parallel_checks,
    synthesize_evidence,
    store_session,
)

@pytest.fixture(autouse=True)
def setup_aws():
    with mock_aws():
        # Setup S3
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.create_bucket(Bucket=settings.S3_UPLOADS_BUCKET)

        # Setup Sessions table
        dynamo = boto3.client("dynamodb", region_name=settings.AWS_REGION)
        dynamo.create_table(
            TableName=settings.DYNAMODB_SESSIONS_TABLE,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        yield

@patch("src.tools.reactive_tools.get_bedrock_runtime_client")
def test_extract_from_image(mock_get_bedrock):
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    s3.put_object(
        Bucket=settings.S3_UPLOADS_BUCKET,
        Key="packaging/test.jpg",
        Body=b"fake_image_bytes"
    )

    mock_client = MagicMock()
    mock_get_bedrock.return_value = mock_client
    mock_client.converse.return_value = {
        "output": {
            "message": {
                "content": [{
                    "text": json.dumps({
                        "drug_name": "Paracetamol",
                        "batch_no": "B99",
                        "confidence": "high",
                        "unreadable_fields": []
                    })
                }]
            }
        }
    }

    res = extract_from_image("packaging/test.jpg")
    assert res["drug_name"] == "Paracetamol"
    assert res["confidence"] == "high"

@patch("src.tools.reactive_tools.opensearch_search")
def test_normalize_and_resolve(mock_search):
    mock_search.return_value = [{
        "_score": 2.0,
        "_source": {"drug_name": "Paracetamol 500mg"}
    }]
    extraction = {"drug_name": "Paracetamol", "batch_no": "B99"}
    res = normalize_and_resolve(extraction)
    assert res["resolved"] is not None
    assert res["resolved"]["drug_name"] == "Paracetamol 500mg"

@patch("src.tools.reactive_tools.check_batch")
@patch("src.tools.reactive_tools.get_manufacturer_history")
@patch("src.tools.reactive_tools.get_community_reports")
def test_run_parallel_checks(mock_reports, mock_mfr, mock_batch):
    mock_batch.return_value = {"found": True}
    mock_mfr.return_value = {"manufacturer_record": None}
    mock_reports.return_value = {"report_count": 0}

    res = run_parallel_checks({"extraction": {"batch_no": "B1"}})
    assert res["batch"]["found"] is True

@patch("src.tools.reactive_tools.get_bedrock_runtime_client")
def test_synthesize_evidence(mock_get_bedrock):
    mock_client = MagicMock()
    mock_get_bedrock.return_value = mock_client
    mock_client.converse.return_value = {
        "output": {
            "message": {
                "content": [{"text": "Official record matches NSQ alert."}]
            }
        }
    }

    res = synthesize_evidence({"drug_name": "Test"}, {"batch": {"found": True}})
    assert res["explanation"] == "Official record matches NSQ alert."
    assert "Absence of a flag is not proof of safety." in res["limitation_statement"]

def test_store_session():
    result_data = {"status": "SUCCESS", "details": "all clear"}
    res = store_session("session-xyz", result_data)
    assert res == result_data

    dynamo = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
    item = table.get_item(Key={"PK": "SESSION#session-xyz", "SK": "RESULT"})
    assert item["Item"]["session_id"] == "session-xyz"
