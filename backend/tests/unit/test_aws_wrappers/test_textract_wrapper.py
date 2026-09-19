import pytest
from unittest.mock import MagicMock, patch
from src.aws_wrappers.textract import TextractWrapper
from src.utils.exceptions import TextractProcessingException

@pytest.fixture
def mock_textract_client():
    with patch("src.aws_wrappers.textract.get_boto_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client

def test_start_table_analysis(mock_textract_client):
    mock_textract_client.start_document_analysis.return_value = {"JobId": "job-12345"}
    wrapper = TextractWrapper()

    job_id = wrapper.start_table_analysis("test-bucket", "test-doc.pdf")
    assert job_id == "job-12345"
    mock_textract_client.start_document_analysis.assert_called_once_with(
        DocumentLocation={"S3Object": {"Bucket": "test-bucket", "Name": "test-doc.pdf"}},
        FeatureTypes=["TABLES"]
    )

def test_poll_and_get_all_blocks_success(mock_textract_client):
    mock_textract_client.get_document_analysis.return_value = {
        "JobStatus": "SUCCEEDED",
        "Blocks": [{"Id": "b1", "BlockType": "TABLE"}]
    }
    wrapper = TextractWrapper()
    blocks = wrapper.poll_and_get_all_blocks("job-12345", poll_interval_sec=0)
    assert len(blocks) == 1
    assert blocks[0]["Id"] == "b1"

def test_poll_and_get_all_blocks_failed(mock_textract_client):
    mock_textract_client.get_document_analysis.return_value = {
        "JobStatus": "FAILED",
        "StatusMessage": "Corrupted PDF"
    }
    wrapper = TextractWrapper()
    with pytest.raises(TextractProcessingException):
        wrapper.poll_and_get_all_blocks("job-12345", poll_interval_sec=0)

def test_detect_document_text(mock_textract_client):
    mock_textract_client.detect_document_text.return_value = {
        "Blocks": [
            {"BlockType": "LINE", "Text": "Batch No: BT9988"},
            {"BlockType": "LINE", "Text": "Mfg Date: 01/2026"}
        ]
    }
    wrapper = TextractWrapper()
    blocks = wrapper.detect_document_text(b"mock_bytes")
    assert len(blocks) == 2
    assert blocks[0]["Text"] == "Batch No: BT9988"

def test_reconstruct_tables():
    wrapper = TextractWrapper()
    # Synthetic table blocks:
    # 1 TABLE block with 2 cells (row 1, col 1 and row 1, col 2)
    # Cell 1 -> WORD "Batch"
    # Cell 2 -> WORD "Result"
    blocks = [
        {
            "Id": "tbl-1",
            "BlockType": "TABLE",
            "Relationships": [{"Type": "CHILD", "Ids": ["cell-1", "cell-2"]}]
        },
        {
            "Id": "cell-1",
            "BlockType": "CELL",
            "RowIndex": 1,
            "ColumnIndex": 1,
            "Relationships": [{"Type": "CHILD", "Ids": ["w-1"]}]
        },
        {
            "Id": "cell-2",
            "BlockType": "CELL",
            "RowIndex": 1,
            "ColumnIndex": 2,
            "Relationships": [{"Type": "CHILD", "Ids": ["w-2"]}]
        },
        {"Id": "w-1", "BlockType": "WORD", "Text": "Batch"},
        {"Id": "w-2", "BlockType": "WORD", "Text": "Result"}
    ]

    tables = wrapper.reconstruct_tables(blocks)
    assert len(tables) == 1
    assert tables[0] == [["Batch", "Result"]]
