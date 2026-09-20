import pytest
from src.pipelines.nsq_ingestion.scraper import (
    parse_listing_html,
    classify_doc_type,
    extract_source_month,
)
from src.pipelines.nsq_ingestion.parser import (
    resolve_header_columns,
    parse_table_rows,
)


def test_classify_doc_type():
    assert classify_doc_type("Alert from Central Drugs Laboratory Kolkata") == "CENTRAL"
    assert classify_doc_type("Notification by Maharashtra FDA Drug Testing Lab") == "STATE"
    assert classify_doc_type("Karnataka State Alert August 2026") == "STATE"


def test_extract_source_month():
    assert extract_source_month("CDSCO NSQ List for August 2026.pdf") == "2026-08"
    assert extract_source_month("Monthly_Alert_Jan_2025.pdf") == "2025-01"


def test_parse_listing_html():
    sample_html = """
    <html>
      <body>
        <ul>
          <li><a href="/downloads/nsq_alert_aug_2026.pdf">Monthly NSQ Alert for August 2026</a></li>
          <li><a href="/downloads/state_maharashtra_sep2026.pdf">Maharashtra State Lab NSQ Report</a></li>
          <li><a href="/other/circular.pdf">General Admin Circular</a></li>
        </ul>
      </body>
    </html>
    """
    candidates = parse_listing_html(sample_html, base_url="https://cdsco.gov.in")
    assert len(candidates) == 3
    assert candidates[0].source_month == "2026-08"
    assert candidates[0].doc_type == "CENTRAL"
    assert candidates[1].doc_type == "STATE"


def test_resolve_header_columns_drift_tolerance():
    # Standard order
    standard_headers = ["S.No", "Drug Name", "Batch No", "Mfg Date", "Exp Date", "Manufacturer", "Reason"]
    col_map = resolve_header_columns(standard_headers)
    assert col_map is not None
    assert col_map[1] == "drug_name"
    assert col_map[2] == "batch_no"

    # Drifted / swapped column order (e.g. Batch No is column 1, Product Name is column 4)
    drifted_headers = ["Index", "B.No", "Testing Lab", "Mfg Date", "Product Name", "Manufactured By", "Result of Test"]
    drift_map = resolve_header_columns(drifted_headers)
    assert drift_map is not None
    assert drift_map[1] == "batch_no"
    assert drift_map[4] == "drug_name"
    assert drift_map[5] == "manufacturer_name"
    assert drift_map[6] == "nsq_reason"


def test_resolve_header_columns_unrecognized():
    unrecognized = ["Col A", "Col B", "Col C", "Col D"]
    assert resolve_header_columns(unrecognized) is None


def test_parse_table_rows_nsq_and_spurious():
    matrix = [
        ["Product Name", "Batch Number", "Mfg Date", "Exp Date", "Manufacturer", "Test Result"],
        ["Paracetamol 500mg", "B-100", "01/2024", "12/2026", "Cipla Ltd", "Fails dissolution test"],
        ["Amoxicillin 250mg", "SP-200", "02/2024", "01/2026", "Fake Lab", "Spurious: Fictitious manufacturer does not exist"],
    ]

    items, error = parse_table_rows(matrix, source_month="2026-09")
    assert error is None
    assert len(items) == 2

    # Row 1: NSQ
    assert items[0]["batch_no_normalized"] == "B-100"
    assert items[0]["alert_status"] == "NSQ"
    assert items[0]["PK"] == "BATCH#B-100"

    # Row 2: SPURIOUS
    assert items[1]["batch_no_normalized"] == "SP-200"
    assert items[1]["alert_status"] == "SPURIOUS"
    assert items[1]["PK"] == "BATCH#SP-200"
