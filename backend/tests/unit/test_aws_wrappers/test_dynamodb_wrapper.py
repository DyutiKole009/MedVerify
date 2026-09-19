import pytest
from moto import mock_aws
import boto3
from src.aws_wrappers.dynamodb import DynamoDBWrapper
from src.aws_wrappers.client_factory import clear_client_cache
from src.utils.exceptions import ConflictException

TABLE_NAME = "MedVerify_Batches"

@pytest.fixture(autouse=True)
def setup_dynamodb():
    with mock_aws():
        clear_client_cache()
        client = boto3.client("dynamodb", region_name="us-east-1")
        # Create Batches table with GSI1
        client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        yield

def test_put_and_get_item():
    wrapper = DynamoDBWrapper()
    item = {
        "PK": "BATCH#ABC1234",
        "SK": "MFR#SUN_PHARMA",
        "drug_name": "Paracetamol 500mg",
        "alert_status": "NSQ",
        "confidence": 0.95
    }
    assert wrapper.put_item(TABLE_NAME, item) is True

    fetched = wrapper.get_item(TABLE_NAME, "BATCH#ABC1234", "MFR#SUN_PHARMA")
    assert fetched is not None
    assert fetched["PK"] == "BATCH#ABC1234"
    assert fetched["drug_name"] == "Paracetamol 500mg"
    assert fetched["confidence"] == 0.95

def test_get_nonexistent_item():
    wrapper = DynamoDBWrapper()
    fetched = wrapper.get_item(TABLE_NAME, "BATCH#NONEXISTENT", "MFR#NONE")
    assert fetched is None

def test_update_item():
    wrapper = DynamoDBWrapper()
    item = {
        "PK": "BATCH#ABC1234",
        "SK": "MFR#SUN_PHARMA",
        "community_report_count": 0
    }
    wrapper.put_item(TABLE_NAME, item)

    updated = wrapper.update_item(
        table_name=TABLE_NAME,
        pk="BATCH#ABC1234",
        sk="MFR#SUN_PHARMA",
        update_expression="SET community_report_count = community_report_count + :inc",
        expression_attribute_values={":inc": 1}
    )
    assert updated["community_report_count"] == 1

def test_conditional_write_failure():
    wrapper = DynamoDBWrapper()
    item = {
        "PK": "BATCH#ABC1234",
        "SK": "MFR#SUN_PHARMA",
        "drug_name": "Paracetamol"
    }
    wrapper.put_item(TABLE_NAME, item)

    # Attempt put with condition that attribute_not_exists(PK) -> should raise ConflictException
    with pytest.raises(ConflictException):
        wrapper.put_item(
            TABLE_NAME,
            item,
            condition_expression="attribute_not_exists(PK)"
        )

def test_delete_item():
    wrapper = DynamoDBWrapper()
    item = {"PK": "BATCH#TO_DEL", "SK": "MFR#1"}
    wrapper.put_item(TABLE_NAME, item)
    assert wrapper.get_item(TABLE_NAME, "BATCH#TO_DEL", "MFR#1") is not None

    wrapper.delete_item(TABLE_NAME, "BATCH#TO_DEL", "MFR#1")
    assert wrapper.get_item(TABLE_NAME, "BATCH#TO_DEL", "MFR#1") is None

def test_query_gsi():
    wrapper = DynamoDBWrapper()
    wrapper.put_item(TABLE_NAME, {
        "PK": "BATCH#1",
        "SK": "MFR#1",
        "GSI1PK": "DRUG#paracetamol",
        "GSI1SK": "BATCH#1"
    })
    wrapper.put_item(TABLE_NAME, {
        "PK": "BATCH#2",
        "SK": "MFR#2",
        "GSI1PK": "DRUG#paracetamol",
        "GSI1SK": "BATCH#2"
    })
    wrapper.put_item(TABLE_NAME, {
        "PK": "BATCH#3",
        "SK": "MFR#3",
        "GSI1PK": "DRUG#amoxicillin",
        "GSI1SK": "BATCH#3"
    })

    items, _ = wrapper.query_gsi(
        table_name=TABLE_NAME,
        index_name="GSI1",
        partition_key="GSI1PK",
        partition_value="DRUG#paracetamol"
    )
    assert len(items) == 2
    assert {i["PK"] for i in items} == {"BATCH#1", "BATCH#2"}

def test_batch_write_items():
    wrapper = DynamoDBWrapper()
    items = [
        {"PK": f"BATCH#BW_{i}", "SK": "META", "count": i}
        for i in range(10)
    ]
    count = wrapper.batch_write_items(TABLE_NAME, items)
    assert count == 10

    fetched = wrapper.get_item(TABLE_NAME, "BATCH#BW_5", "META")
    assert fetched is not None
    assert fetched["count"] == 5
