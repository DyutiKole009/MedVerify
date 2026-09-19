import pytest
from moto import mock_aws
import boto3
import json

from src.pipelines.aggregation.stream_handler import handle_batch_stream_event
from src.pipelines.rag_promotion.feedback_promoter import promote_feedback_sessions_to_kb
from src.config import settings


@pytest.fixture(autouse=True)
def setup_aws():
    with mock_aws():
        dynamo = boto3.client("dynamodb", region_name=settings.AWS_REGION)
        # Batches table with GSI2
        dynamo.create_table(
            TableName=settings.DYNAMODB_BATCHES_TABLE,
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"},
                {"AttributeName": "GSI2SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI2",
                    "KeySchema": [{"AttributeName": "GSI2PK", "KeyType": "HASH"}, {"AttributeName": "GSI2SK", "KeyType": "RANGE"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        # Manufacturers table
        dynamo.create_table(
            TableName=settings.DYNAMODB_MANUFACTURERS_TABLE,
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # Sessions table
        dynamo.create_table(
            TableName=settings.DYNAMODB_SESSIONS_TABLE,
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}, {"AttributeName": "SK", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # S3 KB documents bucket
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.create_bucket(Bucket=settings.S3_KB_DOCUMENTS_BUCKET)
        yield


def test_stream_handler_recompute_metrics():
    dynamo = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    batches_table = dynamo.Table(settings.DYNAMODB_BATCHES_TABLE)

    # Insert 2 NSQ and 1 Spurious batches for manufacturer SUN_PHARMA
    batches_table.put_item(Item={
        "PK": "BATCH#B01",
        "SK": "MFR#SUN_PHARMA",
        "GSI2PK": "MFR#SUN_PHARMA",
        "GSI2SK": "BATCH#B01",
        "alert_status": "NSQ",
        "source_month": "2026-06",
        "manufacturer_name": "Sun Pharma Ltd",
    })
    batches_table.put_item(Item={
        "PK": "BATCH#B02",
        "SK": "MFR#SUN_PHARMA",
        "GSI2PK": "MFR#SUN_PHARMA",
        "GSI2SK": "BATCH#B02",
        "alert_status": "NSQ",
        "source_month": "2026-07",
        "manufacturer_name": "Sun Pharma Ltd",
    })
    batches_table.put_item(Item={
        "PK": "BATCH#B03",
        "SK": "MFR#SUN_PHARMA",
        "GSI2PK": "MFR#SUN_PHARMA",
        "GSI2SK": "BATCH#B03",
        "alert_status": "SPURIOUS",
        "source_month": "2026-08",
        "manufacturer_name": "Sun Pharma Ltd",
    })

    mock_stream_event = {
        "Records": [
            {
                "eventName": "INSERT",
                "dynamodb": {
                    "NewImage": {
                        "manufacturer_id_normalized": {"S": "SUN_PHARMA"}
                    }
                }
            }
        ]
    }

    count = handle_batch_stream_event(mock_stream_event)
    assert count == 1

    mfr_table = dynamo.Table(settings.DYNAMODB_MANUFACTURERS_TABLE)
    item = mfr_table.get_item(Key={"PK": "MFR#SUN_PHARMA"})["Item"]

    assert item["total_nsq_batches"] == 2
    assert item["total_spurious_batches"] == 1
    assert item["last_incident_date"] == "2026-08"


def test_feedback_promotion_to_kb():
    dynamo = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    sessions_table = dynamo.Table(settings.DYNAMODB_SESSIONS_TABLE)

    # Insert an eligible session with helpful feedback
    sessions_table.put_item(Item={
        "PK": "SESSION#valid_sess_101",
        "SK": "META",
        "mode": "DEEP_INVESTIGATE",
        "input_data": {
            "drug_name": "Amoxicillin",
            "batch_no": "AMX99",
            "manufacturer": "Cipla",
        },
        "final_result": {
            "explanation": "Verified against regulatory notices; assay failure detected.",
        },
        "feedback": {
            "helpful": True,
            "comment": "Very detailed and accurate analysis.",
        },
        "promoted_to_kb": False,
    })

    # Insert an ineligible session with unhelpful feedback
    sessions_table.put_item(Item={
        "PK": "SESSION#bad_sess_102",
        "SK": "META",
        "feedback": {
            "helpful": False,
        },
        "promoted_to_kb": False,
    })

    promoted = promote_feedback_sessions_to_kb()
    assert promoted == 1

    # Verify session marked promoted in DynamoDB
    updated_session = sessions_table.get_item(Key={"PK": "SESSION#valid_sess_101", "SK": "META"})["Item"]
    assert updated_session["promoted_to_kb"] is True

    # Verify document and metadata uploaded to S3
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    doc_bytes = s3.get_object(Bucket=settings.S3_KB_DOCUMENTS_BUCKET, Key="case-history/valid_sess_101.txt")["Body"].read()
    assert b"Drug: Amoxicillin" in doc_bytes
    assert b"Investigation Finding:" in doc_bytes

    meta_bytes = s3.get_object(Bucket=settings.S3_KB_DOCUMENTS_BUCKET, Key="case-history/valid_sess_101.txt.metadata.json")["Body"].read()
    meta = json.loads(meta_bytes)
    assert meta["metadataAttributes"]["source_type"] == "case_history"
    assert meta["metadataAttributes"]["session_id"] == "valid_sess_101"
