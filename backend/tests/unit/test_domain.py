import pytest
from src.domain.normalization import (
    normalize_drug_name,
    normalize_batch_no,
    normalize_manufacturer_name,
    build_manufacturer_id,
)
from src.domain.spurious_detector import detect_alert_status


def test_normalize_drug_name():
    assert normalize_drug_name("Paracetamol (500mg) Tab.") == "paracetamol 500mg tab"
    assert normalize_drug_name("  Amoxicillin &   Potassium Clavulanate  ") == "amoxicillin & potassium clavulanate"
    assert normalize_drug_name("") == ""
    assert normalize_drug_name(None) == ""


def test_normalize_batch_no():
    assert normalize_batch_no("B.No. CR-1004") == "CR-1004"
    assert normalize_batch_no("BATCH NO: AB998") == "AB998"
    assert normalize_batch_no("  BNO# 45021  ") == "45021"
    assert normalize_batch_no("XYZ-778") == "XYZ-778"
    assert normalize_batch_no(None) == ""


def test_normalize_manufacturer_name():
    assert normalize_manufacturer_name("Sun Pharmaceuticals Pvt. Ltd.") == "sun pharma ltd"
    assert normalize_manufacturer_name("Cipla Private Limited") == "cipla ltd"
    assert normalize_manufacturer_name("Dr. Reddy's Laboratories Co.") == "dr reddy s lab"
    assert normalize_manufacturer_name("Alkem Labs Limited") == "alkem lab ltd"
    assert normalize_manufacturer_name(None) == ""


def test_build_manufacturer_id():
    assert build_manufacturer_id("Sun Pharmaceuticals Pvt. Ltd.") == "SUN_PHARMA_LTD"
    assert build_manufacturer_id(None) == "UNKNOWN"


def test_detect_alert_status_spurious():
    status, is_spurious = detect_alert_status("The sample is spurious, not manufactured by the genuine firm.")
    assert status == "SPURIOUS"
    assert is_spurious is True

    status, is_spurious = detect_alert_status("Fictitious manufacturer address, does not exist.")
    assert status == "SPURIOUS"
    assert is_spurious is True


def test_detect_alert_status_nsq():
    status, is_spurious = detect_alert_status("Sample fails in dissolution test.")
    assert status == "NSQ"
    assert is_spurious is False

    status, is_spurious = detect_alert_status("Assay value is 82.5% against standard 95-105%.")
    assert status == "NSQ"
    assert is_spurious is False


def test_detect_alert_status_none():
    status, is_spurious = detect_alert_status("")
    assert status == "NONE"
    assert is_spurious is False

    status, is_spurious = detect_alert_status(None)
    assert status == "NONE"
    assert is_spurious is False
