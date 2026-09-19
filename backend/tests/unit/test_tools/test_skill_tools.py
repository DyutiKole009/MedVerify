import pytest
from moto import mock_aws
import boto3
from unittest.mock import patch, MagicMock
from src.config import settings
from src.tools.skill_tools import (
    check_batch,
    get_manufacturer_history,
    get_notice,
    get_case_history,
    get_community_reports,
    search_drug,
)

@pytest.fixture(autouse=True)
def setup_aws():
    with mock_aws():
        # Setup DynamoDB
        dynamo = boto3.client("dynamodb", region_name=settings.AWS_REGION)
        # Batches table
        dynamo.create_table(
            TableName=settings.DYNAMODB_BATCHES_TABLE,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"},
                {"AttributeName": "GSI2SK", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI2",
                    "KeySchema": [
                        {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI2SK", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        # Manufacturers table
        dynamo.create_table(
            TableName=settings.DYNAMODB_MANUFACTURERS_TABLE,
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        # Sessions table
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
        # Reports table
        dynamo.create_table(
            TableName=settings.DYNAMODB_REPORTS_TABLE,
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [{"AttributeName": "GSI1PK", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "GSI2",
                    "KeySchema": [{"AttributeName": "GSI2PK", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        # Setup S3
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.create_bucket(Bucket=settings.S3_RAW_DOCUMENTS_BUCKET)
        yield

def test_check_batch_found():
    dynamo = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    table = dynamo.Table(settings.DYNAMODB_BATCHES_TABLE)
    table.put_item(Item={
        "PK": "BATCH#B1001",
        "SK": "MFR#CIPLA",
        "drug_name": "Paracetamol 500mg",
        "drug_name_normalized": "paracetamol 500mg",
        "community_flag": True,
    })

    res = check_batch("B1001", drug_name="Paracetamol 500mg", manufacturer="CIPLA")
    assert res["found"] is True
    assert res["community_flag"] is True
    assert res["batch_record"]["PK"] == "BATCH#B1001"

def test_check_batch_not_found():
    res = check_batch("NONEXISTENT")
    assert res["found"] is False
    assert res["batch_record"] is None

def test_get_manufacturer_history():
    dynamo = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    mfr_table = dynamo.Table(settings.DYNAMODB_MANUFACTURERS_TABLE)
    mfr_table.put_item(Item={"PK": "MFR#SUN#PHARMA", "name": "Sun Pharma"})

    batch_table = dynamo.Table(settings.DYNAMODB_BATCHES_TABLE)
    batch_table.put_item(Item={
        "PK": "BATCH#B2001",
        "SK": "MFR#SUN#PHARMA",
        "GSI2PK": "MFR#SUN#PHARMA",
        "GSI2SK": "BATCH#B2001",
    })

    res = get_manufacturer_history("Sun Pharma")
    assert res["manufacturer_record"]["name"] == "Sun Pharma"
    assert len(res["recent_batches"]) == 1

def test_get_notice():
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    s3.put_object(
        Bucket=settings.S3_RAW_DOCUMENTS_BUCKET,
        Key="notices/test.txt",
        Body=b"Official alert contents"
    )

    res = get_notice("notices/test.txt")
    assert res["notice_text"] == "Official alert contents"
    assert "s3://" in res["source_url"]

def test_get_case_history():
    dynamo = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)
    table.put_item(Item={
        "PK": "SESSION#sess-01",
        "SK": "RESULT",
        "status": "COMPLETED",
    })

    res = get_case_history("sess-01")
    assert res["session_record"]["status"] == "COMPLETED"

def test_get_community_reports():
    dynamo = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    table = dynamo.Table(settings.DYNAMODB_REPORTS_TABLE)
    table.put_item(Item={
        "PK": "REP#1",
        "GSI1PK": "BATCH#B3001",
        "status": "APPROVED",
    })

    res = get_community_reports(batch_no="B3001")
    assert res["report_count"] == 1
    assert res["community_flag"] is True

@patch("src.tools.skill_tools.opensearch_search")
def test_search_drug(mock_search):
    mock_search.return_value = [
        {
            "_score": 3.5,
            "_source": {
                "drug_name": "Amoxicillin",
                "manufacturer_name": "Alkem",
                "batch_no": "AMX50",
            },
        }
    ]

    res = search_drug("amoxicil")
    assert len(res["candidates"]) == 1
    assert res["candidates"][0]["drug_name"] == "Amoxicillin"
