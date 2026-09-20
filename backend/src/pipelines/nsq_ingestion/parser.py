"""
Table parser with column drift tolerance for CDSCO NSQ PDFs (§5.2 step 4 & step 5).
Maps variable monthly table headers into structured batches records.
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from src.domain.normalization import (
    normalize_drug_name,
    normalize_batch_no,
    normalize_manufacturer_name,
    build_manufacturer_id,
)
from src.domain.spurious_detector import detect_alert_status

HEADER_SYNONYMS = {
    "reporting_lab": ["testing laboratory", "testing lab", "reported by", "analysed at", "laboratory", "lab"],
    "drug_name": ["product name", "name of drug", "name of the drug", "drug name", "drug", "composition"],
    "batch_no": ["batch number", "batch no", "b. no.", "b.no", "bno", "batch"],
    "mfg_date": ["manufacturing date", "date of mfg", "mfg date", "mfd", "mfg"],
    "expiry_date": ["date of expiry", "expiry date", "exp date", "exp. date", "exp"],
    "manufacturer_name": ["name and address of manufacturer", "name of manufacturer", "manufactured by", "manufacturer", "mfr"],
    "nsq_reason": ["result of test", "test result", "nsq result", "reason for failure", "declared as", "reason", "failing in", "assay"],
}


def resolve_header_columns(header_row: List[str]) -> Optional[Dict[int, str]]:
    """
    Matches header row cells against synonym lists to build a column_index -> field_name map (§5.2 step 4).
    Returns None if fewer than 4 required fields are identified (column drift protection).
    """
    col_map: Dict[int, str] = {}
    used_fields = set()

    for idx, cell_text in enumerate(header_row):
        clean_cell = cell_text.lower().strip()
        for field_name, synonyms in HEADER_SYNONYMS.items():
            if field_name in used_fields:
                continue
            for syn in synonyms:
                if syn in clean_cell:
                    col_map[idx] = field_name
                    used_fields.add(field_name)
                    break
            if idx in col_map:
                break

    # If fewer than 4 expected fields matched, abort parsing to avoid bad data writes (§5.2)
    if len(col_map) < 4:
        return None

    return col_map


def parse_table_rows(
    table_matrix: List[List[str]],
    source_month: str = "2026-09",
    source_document_s3_key: str = "",
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Parses a 2D table matrix (e.g. from Textract or bootstrap CSV) into structured Batches items.
    Returns: (parsed_items, error_reason)
    """
    if not table_matrix or len(table_matrix) < 2:
        return [], "Table matrix has no data rows"

    header_row = table_matrix[0]
    col_map = resolve_header_columns(header_row)

    if not col_map:
        return [], "header row unrecognized (< 4 columns matched)"

    now_iso = datetime.now(timezone.utc).isoformat()
    parsed_items: List[Dict[str, Any]] = []

    for row in table_matrix[1:]:
        if not any(cell.strip() for cell in row):
            continue

        raw_data: Dict[str, str] = {}
        for col_idx, field_name in col_map.items():
            if col_idx < len(row):
                raw_data[field_name] = row[col_idx].strip()

        batch_raw = raw_data.get("batch_no", "")
        drug_raw = raw_data.get("drug_name", "")
        mfr_raw = raw_data.get("manufacturer_name", "")
        reason_raw = raw_data.get("nsq_reason", "")

        if not batch_raw and not drug_raw:
            continue

        batch_norm = normalize_batch_no(batch_raw)
        drug_norm = normalize_drug_name(drug_raw)
        mfr_norm = normalize_manufacturer_name(mfr_raw)
        mfr_id = build_manufacturer_id(mfr_raw)

        alert_status, is_spurious = detect_alert_status(reason_raw)

        item: Dict[str, Any] = {
            "PK": f"BATCH#{batch_norm}",
            "SK": f"MFR#{mfr_id}",
            "batch_no": batch_raw,
            "batch_no_normalized": batch_norm,
            "drug_name": drug_raw,
            "drug_name_normalized": drug_norm,
            "manufacturer_name": mfr_raw,
            "manufacturer_id_normalized": mfr_id,
            "mfg_date": raw_data.get("mfg_date", ""),
            "expiry_date": raw_data.get("expiry_date", ""),
            "alert_status": alert_status,
            "nsq_reason": reason_raw,
            "reporting_lab": raw_data.get("reporting_lab", "CDL"),
            "source_month": source_month,
            "source_document_s3_key": source_document_s3_key,
            "community_flag": False,
            "community_report_count": 0,
            "ingested_at": now_iso,
            "last_updated": now_iso,
            # GSI1: Search by drug
            "GSI1PK": f"DRUG#{drug_norm}",
            "GSI1SK": f"BATCH#{batch_norm}",
            # GSI2: Search by manufacturer
            "GSI2PK": f"MFR#{mfr_id}",
            "GSI2SK": f"BATCH#{batch_norm}",
        }

        parsed_items.append(item)

    return parsed_items, None
