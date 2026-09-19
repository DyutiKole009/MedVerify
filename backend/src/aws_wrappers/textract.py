"""
Amazon Textract wrapper for table extraction from NSQ alert PDFs and packaging OCR fallback.
"""
from typing import Dict, Any, List, Optional, Tuple
import time
from src.aws_wrappers.base import BaseAWSWrapper, catch_aws_errors
from src.aws_wrappers.client_factory import get_boto_client
from src.utils.exceptions import TextractProcessingException
from src.utils.logger import logger

class TextractWrapper(BaseAWSWrapper):
    """
    Encapsulates Amazon Textract operations.
    Handles asynchronous multi-page table extraction and synchronous line detection.
    """
    def __init__(self):
        super().__init__("Textract")
        self.client = get_boto_client("textract")

    @catch_aws_errors("StartDocumentAnalysis")
    def start_table_analysis(self, s3_bucket: str, s3_key: str) -> str:
        """
        Initiates asynchronous table analysis on multi-page PDF documents stored in S3 (§5.2).
        Returns JobId.
        """
        response = self.client.start_document_analysis(
            DocumentLocation={"S3Object": {"Bucket": s3_bucket, "Name": s3_key}},
            FeatureTypes=["TABLES"]
        )
        job_id = response.get("JobId")
        logger.info(f"Started Textract table analysis job {job_id} for s3://{s3_bucket}/{s3_key}")
        return job_id

    @catch_aws_errors("GetDocumentAnalysis")
    def get_document_analysis(
        self,
        job_id: str,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetches a single page of document analysis results."""
        kwargs: Dict[str, Any] = {"JobId": job_id}
        if next_token:
            kwargs["NextToken"] = next_token
        return self.client.get_document_analysis(**kwargs)

    def poll_and_get_all_blocks(
        self,
        job_id: str,
        poll_interval_sec: int = 3,
        max_attempts: int = 120
    ) -> List[Dict[str, Any]]:
        """
        Polls until the Textract job succeeds and gathers all block items across pages.
        """
        attempts = 0
        while attempts < max_attempts:
            res = self.get_document_analysis(job_id)
            status = res.get("JobStatus")

            if status == "SUCCEEDED":
                blocks = res.get("Blocks", [])
                next_token = res.get("NextToken")
                while next_token:
                    page_res = self.get_document_analysis(job_id, next_token=next_token)
                    blocks.extend(page_res.get("Blocks", []))
                    next_token = page_res.get("NextToken")
                return blocks
            elif status == "FAILED":
                msg = res.get("StatusMessage", "Unknown Textract failure")
                logger.error(f"Textract job {job_id} failed: {msg}")
                raise TextractProcessingException("Textract", f"Job failed: {msg}")

            time.sleep(poll_interval_sec)
            attempts += 1

        raise TextractProcessingException("Textract", f"Job {job_id} timed out after polling.")

    @catch_aws_errors("DetectDocumentText")
    def detect_document_text(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Synchronous raw text detection used as fallback for blister packaging photos (§9.5).
        Returns a list of LINE and WORD blocks.
        """
        response = self.client.detect_document_text(Document={"Bytes": image_bytes})
        return response.get("Blocks", [])

    def reconstruct_tables(self, blocks: List[Dict[str, Any]]) -> List[List[List[str]]]:
        """
        Reconstructs structured 2D string matrices (tables) from Textract block relationships (§5.2).
        Returns: List of tables, where each table is a List of rows, and each row is a List of cell text.
        """
        # Index blocks by Id for quick relationship traversal
        block_map = {b["Id"]: b for b in blocks if "Id" in b}
        tables: List[List[List[str]]] = []

        table_blocks = [b for b in blocks if b.get("BlockType") == "TABLE"]

        for table in table_blocks:
            relationships = table.get("Relationships", [])
            cell_ids: List[str] = []
            for rel in relationships:
                if rel.get("Type") == "CHILD":
                    cell_ids.extend(rel.get("Ids", []))

            # Group cells by (RowIndex, ColumnIndex)
            cells_by_pos: Dict[Tuple[int, int], str] = {}
            max_row = 0
            max_col = 0

            for cid in cell_ids:
                cell_block = block_map.get(cid)
                if not cell_block or cell_block.get("BlockType") != "CELL":
                    continue

                r_idx = cell_block.get("RowIndex", 1)
                c_idx = cell_block.get("ColumnIndex", 1)
                max_row = max(max_row, r_idx)
                max_col = max(max_col, c_idx)

                # Extract text inside cell
                cell_text_parts = []
                for cell_rel in cell_block.get("Relationships", []):
                    if cell_rel.get("Type") == "CHILD":
                        for word_id in cell_rel.get("Ids", []):
                            word_block = block_map.get(word_id)
                            if word_block and word_block.get("BlockType") in ("WORD", "SELECTION_ELEMENT"):
                                if "Text" in word_block:
                                    cell_text_parts.append(word_block["Text"])

                cells_by_pos[(r_idx, c_idx)] = " ".join(cell_text_parts).strip()

            # Build 2D matrix
            table_matrix: List[List[str]] = []
            for r in range(1, max_row + 1):
                row_cells: List[str] = []
                for c in range(1, max_col + 1):
                    row_cells.append(cells_by_pos.get((r, c), ""))
                table_matrix.append(row_cells)

            if table_matrix:
                tables.append(table_matrix)

        return tables
