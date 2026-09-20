import pytest
from moto import mock_aws
import boto3
from fastapi.testclient import TestClient
import jwt
from unittest.mock import patch, MagicMock

from src.main import app
from src.config import settings

client = TestClient(app)


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
                    "KeySchema": [
                        {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        # Sessions table
        dynamo.create_table(
            TableName=settings.DYNAMODB_SESSIONS_TABLE,
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}, {"AttributeName": "SK", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # Manufacturers table
        dynamo.create_table(
            TableName=settings.DYNAMODB_MANUFACTURERS_TABLE,
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # Reports table
        dynamo.create_table(
            TableName=settings.DYNAMODB_REPORTS_TABLE,
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"},
                {"AttributeName": "GSI2SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [{"AttributeName": "GSI1PK", "KeyType": "HASH"}, {"AttributeName": "GSI1SK", "KeyType": "RANGE"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI2",
                    "KeySchema": [{"AttributeName": "GSI2PK", "KeyType": "HASH"}, {"AttributeName": "GSI2SK", "KeyType": "RANGE"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        # S3 Uploads
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.create_bucket(Bucket=settings.S3_UPLOADS_BUCKET)
        yield


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_check_endpoint():
    response = client.post("/check", json={"batch_no": "B99881"})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status_category"] == "NO_MATCH"
    assert "Absence of a flag is not proof of safety." in data["limitation_statement"]
    assert "orchestrator_decision" in data


def test_check_endpoint_empty():
    response = client.post("/check", json={})
    assert response.status_code == 400


def test_presign_upload_endpoint():
    response = client.post("/uploads/presign", json={"filename": "blister_pack.jpg", "content_type": "image/jpeg"})
    assert response.status_code == 200
    data = response.json()
    assert "upload_url" in data
    assert "packaging-photos/" in data["s3_key"]


@patch("src.routers.investigate.extract_from_image")
def test_investigate_endpoint(mock_extract):
    mock_extract.return_value = {
        "drug_name": "Paracetamol",
        "batch_no": "B99881",
        "manufacturer_name": "Cipla",
        "confidence": "high",
        "ocr_confidence": 0.95,
        "unreadable_fields": [],
    }
    response = client.post("/investigate", json={"image_s3_key": "packaging-photos/photo_1.jpg"})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "DONE"


def test_investigate_deep_endpoint():
    response = client.post(
        "/investigate/deep",
        json={"description": "Tablets have an unusual texture and odor.", "drug_name": "Paracetamol"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "PROCESSING"


def test_report_unauthorized():
    response = client.post(
        "/reports",
        json={"drug_name": "Paracetamol", "description": "Side effect"},
    )
    assert response.status_code == 401


def test_report_authorized():
    token = jwt.encode({"sub": "user_123", "email": "user@medverify.io", "custom:role": "consumer"}, "secret", algorithm="HS256")
    response = client.post(
        "/reports",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "drug_name": "Paracetamol 500mg",
            "batch_no": "BT123",
            "issue_type": "SIDE_EFFECT",
            "description": "Patient experienced nausea.",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "report_id" in data
    assert data["status"] == "PENDING"


def test_session_feedback_and_get():
    # First create a session via /check
    res = client.post("/check", json={"batch_no": "TEST_SESSION"})
    session_id = res.json()["session_id"]

    # Submit feedback
    fb_res = client.post(f"/sessions/{session_id}/feedback", json={"helpful": True, "comment": "Accurate alert."})
    assert fb_res.status_code == 200
    assert fb_res.json()["recorded"] is True

    # Retrieve session
    get_res = client.get(f"/sessions/{session_id}")
    assert get_res.status_code == 200
    session_data = get_res.json()
    assert session_data["feedback"]["helpful"] is True
    assert session_data["feedback"]["comment"] == "Accurate alert."


def test_admin_update_role_forbidden():
    # Non-admin user trying to access admin endpoint
    token = jwt.encode({"sub": "user_123", "custom:role": "consumer"}, "secret", algorithm="HS256")
    response = client.patch(
        "/admin/users/target_user/role",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "pharmacist"},
    )
    assert response.status_code == 403


def test_admin_update_role_success():
    # Admin user
    token = jwt.encode({"sub": "admin_root", "custom:role": "admin"}, "secret", algorithm="HS256")
    response = client.patch(
        "/admin/users/target_user/role",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "pharmacist"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
