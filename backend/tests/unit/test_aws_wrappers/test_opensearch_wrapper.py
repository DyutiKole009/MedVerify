import pytest
from unittest.mock import MagicMock, patch
from src.aws_wrappers.opensearch import OpenSearchWrapper

@pytest.fixture
def mock_requests():
    with patch("src.aws_wrappers.opensearch.requests.request") as mock_req:
        yield mock_req

def test_search_fuzzy(mock_requests):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "doc1",
                    "_score": 2.45,
                    "_source": {"drug_name": "Paracetamol", "manufacturer": "Sun Pharma"}
                }
            ]
        }
    }
    mock_requests.return_value = mock_response

    wrapper = OpenSearchWrapper(endpoint="https://test-opensearch.us-east-1.aoss.amazonaws.com")
    hits = wrapper.search_fuzzy(
        index_name="medverify-drugs",
        field_name="drug_name_normalized",
        query_text="paracetaml"
    )

    assert len(hits) == 1
    assert hits[0]["id"] == "doc1"
    assert hits[0]["score"] == 2.45
    assert hits[0]["source"]["drug_name"] == "Paracetamol"

def test_index_document(mock_requests):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"result": "created"}
    mock_requests.return_value = mock_response

    wrapper = OpenSearchWrapper(endpoint="https://test-opensearch.us-east-1.aoss.amazonaws.com")
    res = wrapper.index_document(
        index_name="medverify-drugs",
        doc_id="drug-1",
        document={"name": "Amoxicillin"}
    )
    assert res == {"result": "created"}
