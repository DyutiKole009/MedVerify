import pytest
from unittest.mock import patch, MagicMock
from src.tools.deep_tools import (
    retrieve_related_notices,
    retrieve_similar_cases,
)

@patch("src.tools.deep_tools.opensearch_search")
def test_retrieve_related_notices(mock_search):
    mock_search.return_value = [
        {
            "_source": {"search_text": "Notice of quality failure", "s3_uri": "s3://bucket/notice1.txt"},
            "_score": 0.95,
        }
    ]

    res = retrieve_related_notices.invoke({"query_text": "paracetamol failure"})
    assert len(res["results"]) == 1
    assert res["results"][0]["score"] == 0.95
    assert res["results"][0]["s3_uri"] == "s3://bucket/notice1.txt"

@patch("src.tools.deep_tools.skill_get_community_reports")
def test_retrieve_similar_cases(mock_skill):
    mock_skill.return_value = {
        "count": 1,
        "reports": [{"report_id": "rep-1", "issue_type": "PACKAGING_DEFECT"}],
    }

    res = retrieve_similar_cases.invoke({"batch_no": "B-123", "drug_name": "Paracetamol"})
    assert res["count"] == 1
    assert res["reports"][0]["report_id"] == "rep-1"
