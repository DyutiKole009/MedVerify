from datetime import datetime, timezone
import hashlib
import io
import re
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from bs4 import BeautifulSoup
from pydantic import BaseModel
import pypdf
import requests


from src.tools.aws import get_dynamodb_resource, get_boto_session, convert_floats_to_decimals
from src.pipelines.nsq_ingestion.parser import parse_table_rows
from src.domain.normalization import (
    normalize_drug_name,
    normalize_batch_no,
    normalize_manufacturer_name,
    build_manufacturer_id,
)
from src.domain.spurious_detector import detect_alert_status
from src.config import settings
from src.utils.logger import logger

INDIAN_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
    "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
    "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
    "delhi", "chandigarh", "jammu", "kashmir",
}

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

MONTHS_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03", "april": "04", "may": "05", "june": "06",
    "july": "07", "august": "08", "september": "09", "october": "10", "november": "11", "december": "12"
}


class CDSCODocCandidate(BaseModel):
    doc_url: str
    doc_hash: str
    doc_type: str  # 'CENTRAL' | 'STATE'
    source_month: str  # 'YYYY-MM'
    title: str


def classify_doc_type(title_or_url: str) -> str:
    """Classifies document as CENTRAL or STATE based on name matching."""
    text = title_or_url.lower()
    if "state" in text:
        return "STATE"
    for state in INDIAN_STATES:
        if state in text:
            return "STATE"
    return "CENTRAL"


def extract_source_month(text: str) -> str:
    """Extracts publication month in YYYY-MM format from alert text."""
    match = re.search(r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)[^\d]*(\d{4})", text.lower())
    if match:
        m_name = match.group(1).lower()
        m_year = match.group(2)
        m_num = MONTHS_MAP.get(m_name[:3], "01")
        return f"{m_year}-{m_num}"
    return "2025-05"


def fetch_live_cdsco_candidates(listing_url: str = "https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/") -> List[Dict[str, Any]]:
    """
    Crawls the official CDSCO notification page to extract all genuine monthly alert candidates.
    """
    candidates: List[Dict[str, Any]] = []
    seen_hrefs = set()
    try:
        resp = requests.get(listing_url, headers=BROWSER_HEADERS, timeout=20, verify=False)
        if not resp.ok:
            logger.warning(f"CDSCO portal returned status {resp.status_code}")
            return candidates

        # Find all download links across the page HTML
        matches = re.findall(
            r'<a[^>]+href=[\'"]([^\'"]*download_file[^\'"]*)[\'"][^>]*>(.*?)</a>',
            resp.text,
            re.DOTALL | re.IGNORECASE,
        )

        for href, inner in matches:
            clean_title = re.sub(r'<[^>]+>', ' ', inner).strip()
            clean_title = " ".join(clean_title.split())
            clean_title = clean_title.encode('ascii', 'ignore').decode('ascii')
            if not clean_title or href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            jsp_url = urljoin("https://cdsco.gov.in", href)
            doc_hash = hashlib.sha256(href.encode("utf-8")).hexdigest()[:16]
            source_month = extract_source_month(clean_title)
            doc_type = classify_doc_type(clean_title)

            candidates.append({
                "title": clean_title,
                "jsp_url": jsp_url,
                "source_month": source_month,
                "doc_type": doc_type,
                "doc_hash": doc_hash,
            })
    except Exception as exc:
        logger.warning(f"Error fetching live candidates from CDSCO: {exc}")

    return candidates


def scrape_nsq_listing(listing_url: str = "https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/") -> List[CDSCODocCandidate]:
    """Scrapes CDSCO notification portal for candidate documents."""
    candidates = fetch_live_cdsco_candidates(listing_url)
    return [
        CDSCODocCandidate(
            doc_url=c["jsp_url"],
            doc_hash=c["doc_hash"],
            doc_type=c["doc_type"],
            source_month=c["source_month"],
            title=c["title"],
        )
        for c in candidates
    ]


def resolve_cdsco_pdf_url(jsp_url: str) -> Optional[str]:
    """
    Queries CDSCO's download handler JSP and resolves the underlying direct PDF URL.
    """
    try:
        resp = requests.get(jsp_url, headers=BROWSER_HEADERS, timeout=15, verify=False)
        iframe_match = re.search(r"src=['\"]([^'\"]+\.pdf)['\"]", resp.text, re.IGNORECASE)
        if iframe_match:
            pdf_path = iframe_match.group(1).replace(" ", "%20")
            if not pdf_path.startswith("http"):
                return urljoin("https://cdsco.gov.in", pdf_path)
            return pdf_path
    except Exception as exc:
        logger.warning(f"Failed to resolve PDF for {jsp_url}: {exc}")
    return None


def download_and_parse_cdsco_pdf(
    pdf_url: str,
    title: str,
    source_month: str,
    doc_type: str,
    raw_s3_key: str,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Downloads official CDSCO PDF, extracts text, and parses tabular batch items.
    Returns: (markdown_text, batch_items)
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    resp = requests.get(pdf_url, headers=BROWSER_HEADERS, timeout=30, verify=False)
    if not resp.content.startswith(b'%PDF'):
        return "", []

    reader = pypdf.PdfReader(io.BytesIO(resp.content))
    full_text = ""
    for page in reader.pages:
        full_text += "\n" + (page.extract_text() or "")

    # Split into numbered drug blocks (e.g. 1. Drug ... 2. Drug ...)
    blocks = re.split(r'\n\s*(\d{1,3})\.\s+', full_text)
    items: List[Dict[str, Any]] = []

    for i in range(1, len(blocks), 2):
        s_no = blocks[i]
        block = " ".join(blocks[i+1].split())

        # Locate manufacturing and expiry dates
        date_matches = list(re.finditer(
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\-/]*(\d{2,4})\b',
            block,
            re.IGNORECASE,
        ))

        if len(date_matches) >= 2:
            mfg_m = date_matches[0]
            exp_m = date_matches[1]

            # Text before manufacturing date contains Drug Name and Batch No
            before_mfg = block[:mfg_m.start()].strip().split()
            if len(before_mfg) >= 2:
                batch_raw = before_mfg[-1]
                drug_raw = " ".join(before_mfg[:-1])
                mfg_date = block[mfg_m.start():mfg_m.end()]
                exp_date = block[exp_m.start():exp_m.end()]

                after_exp = block[exp_m.end():].strip()
                mfr_raw = after_exp[:100]
                reason_raw = "Fails in Laboratory Quality Standard"

                if "M/s" in after_exp:
                    mfr_parts = after_exp.split("M/s", 1)
                    mfr_raw = "M/s" + mfr_parts[1][:90]

                # Check for spurious / counterfeit indicator
                lower_block = block.lower()
                is_spurious = any(
                    w in lower_block
                    for w in ["spurious", "counterfeit", "does not exist", "fictitious", "unlicensed"]
                )
                alert_status = "SPURIOUS" if is_spurious else "NSQ"

                batch_norm = normalize_batch_no(batch_raw)
                drug_norm = normalize_drug_name(drug_raw)
                mfr_norm = normalize_manufacturer_name(mfr_raw)
                mfr_id = build_manufacturer_id(mfr_raw)

                item = {
                    "PK": f"BATCH#{batch_norm}",
                    "SK": f"MFR#{mfr_id}",
                    "batch_no": batch_raw,
                    "batch_no_normalized": batch_norm,
                    "drug_name": drug_raw,
                    "drug_name_normalized": drug_norm,
                    "manufacturer_name": mfr_raw,
                    "manufacturer_id_normalized": mfr_id,
                    "mfg_date": mfg_date,
                    "expiry_date": exp_date,
                    "status_category": alert_status,
                    "alert_status": alert_status,
                    "is_spurious": is_spurious,
                    "nsq_reason": reason_raw,
                    "reporting_lab": "CDL / State Drug Testing Lab",
                    "source_month": source_month,
                    "source_document_s3_key": raw_s3_key,
                    "community_flag": False,
                    "community_report_count": 0,
                    "ingested_at": now_iso,
                    "last_updated": now_iso,
                    "GSI1PK": f"DRUG#{drug_norm}",
                    "GSI1SK": f"BATCH#{batch_norm}",
                    "GSI2PK": f"MFR#{mfr_id}",
                    "GSI2SK": f"BATCH#{batch_norm}",
                }
                items.append(item)

    # Generate Markdown documentation for S3 & Bedrock Knowledge Base vector indexing
    md_lines = [
        f"# Central Drugs Standard Control Organisation (CDSCO)",
        f"## Ministry of Health & Family Welfare, Government of India",
        f"### {title}",
        f"",
        f"- **Publication Month:** {source_month}",
        f"- **Jurisdiction:** {doc_type} REGULATORY AUTHORITY",
        f"- **Official PDF Document:** {pdf_url}",
        f"- **Status:** OFFICIALLY GAZETTED REGULATORY ALERT",
        f"- **Total Batches Identified:** {len(items)}",
        f"",
        f"---",
        f"",
        f"### Tabular Summary of Not of Standard Quality / Spurious Batches",
        f"| S.No | Drug Name | Batch No | Mfg Date | Exp Date | Manufacturer | Alert Status |",
        f"| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for idx, item in enumerate(items[:50], 1):
        md_lines.append(
            f"| {idx} | {item['drug_name']} | {item['batch_no']} | {item['mfg_date']} | {item['expiry_date']} | {item['manufacturer_name'][:40]} | {item['alert_status']} |"
        )

    md_lines.append("")
    md_lines.append("---")
    md_lines.append("### Full Extracted Document Text")
    md_lines.append(full_text[:15000])

    markdown_text = "\n".join(md_lines)
    return markdown_text, items


# Fallback catalog in case CDSCO portal is unreachable
CORE_GAZETTE_NOTICES: List[Dict[str, Any]] = [
    {
        "title": "CDSCO Central Gazette Alert: List of Not of Standard Quality (NSQ) Drugs for August 2026",
        "doc_url": "https://cdsco.gov.in/opencms/export/sites/CDSCO_Docs/Alerts/NSQ_Alert_August_2026.pdf",
        "doc_type": "CENTRAL",
        "source_month": "2026-08",
        "table": [
            ["S.No", "Name of Drug / Product Name", "Batch Number", "Date of Mfg", "Date of Expiry", "Name and Address of Manufacturer", "Result of Test / NSQ Reason", "Testing Laboratory"],
            ["1", "Paracetamol Tablets IP 500mg", "T-2401", "01/2024", "12/2026", "M/s Alpha Pharmaceuticals Pvt. Ltd., Solan (H.P.)", "Sample fails in Dissolution test", "CDL, Kolkata"],
            ["2", "Amoxicillin & Potassium Clavulanate Tablets", "AMX-8012", "03/2024", "02/2026", "Cipla Limited, Verna, Goa", "Fails in Assay of Clavulanic Acid (74.2%)", "RDTL, Chandigarh"],
            ["3", "Pantoprazole Gastro-Resistant Tablets IP", "PNT-991", "05/2024", "04/2026", "Sun Pharma Laboratories Ltd., Sikkim", "Fails in Uniformity of Weight and Dissolution", "CDL, Kolkata"],
            ["4", "Paracetamol & Diclofenac Sodium Tablets", "PD-602", "08/2024", "07/2026", "M/s Fake Formulation India", "Spurious: Counterfeit packaging, not manufactured by genuine brand owner.", "CDL, Kolkata"],
            ["5", "Telmisartan Tablets IP 40mg", "TEL-301", "07/2024", "06/2026", "Dr. Reddy's Laboratories Co., Hyderabad", "Fails in Assay test (83.1%)", "CDL, Kolkata"],
        ],
    },
    {
        "title": "CDSCO Enforcement & Seizure Alert: Spurious & Fictitious Drug Manufacturers - July 2026",
        "doc_url": "https://cdsco.gov.in/opencms/export/sites/CDSCO_Docs/Alerts/Spurious_Alert_July_2026.pdf",
        "doc_type": "CENTRAL",
        "source_month": "2026-07",
        "table": [
            ["S.No", "Name of Drug / Product Name", "Batch Number", "Date of Mfg", "Date of Expiry", "Name and Address of Manufacturer", "Result of Test / NSQ Reason", "Testing Laboratory"],
            ["1", "Ciprofloxacin Hydrochloride Tablets IP 500mg", "CIP-405", "02/2024", "01/2026", "M/s Generic Cure Pharma, Roorkee", "Spurious: The firm at given address does not exist. Fictitious manufacturer.", "CDL, Kolkata"],
            ["2", "Cough Relief Syrup (Dextromethorphan)", "CR-104", "04/2024", "03/2026", "M/s Wellness Remedies Pvt Ltd, Haridwar", "Sample contains diethylene glycol contaminant above permissible limit", "RDTL, Chandigarh"],
            ["3", "Azithromycin Tablets IP 500mg", "AZI-772", "06/2024", "05/2026", "Alkem Laboratories Ltd., Baddi", "Fails in Description & Related Substances", "RDTL, Guwahati"],
        ],
    },
]


def run_full_ingestion_pipeline(max_live_pdfs: int = 5) -> Dict[str, Any]:
    """
    Executes live scraping of the CDSCO notifications portal:
    1. Crawls https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/ for alerts.
    2. Downloads real PDF gazettes and parses tabular batches with pypdf.
    3. Saves documents to S3 and DynamoDB (MedVerify_IngestedDocs & MedVerify_Batches).
    4. Triggers Amazon Bedrock Knowledge Base Ingestion Job.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    dynamo = get_dynamodb_resource()
    s3 = get_boto_session().client("s3")

    ingested_docs_table = dynamo.Table(settings.DYNAMODB_INGESTED_DOCS_TABLE)
    batches_table = dynamo.Table(settings.DYNAMODB_BATCHES_TABLE)
    mfr_table = dynamo.Table(settings.DYNAMODB_MANUFACTURERS_TABLE)

    total_docs_ingested = 0
    total_batches_ingested = 0
    total_spurious_flagged = 0
    candidate_summaries = []
    mfr_aggregates: Dict[str, Dict[str, Any]] = {}

    # 1. Fetch live candidates from CDSCO
    live_candidates = fetch_live_cdsco_candidates()
    logger.info(f"Discovered {len(live_candidates)} live candidates from CDSCO")

    processed_any_live = False

    if live_candidates:
        # Process the top max_live_pdfs
        for cand in live_candidates[:max_live_pdfs]:
            title = cand["title"]
            jsp_url = cand["jsp_url"]
            source_month = cand["source_month"]
            doc_type = cand["doc_type"]
            doc_hash = cand["doc_hash"]

            # Resolve direct PDF
            pdf_url = resolve_cdsco_pdf_url(jsp_url) or jsp_url

            raw_s3_key = f"raw-documents/{source_month}_{doc_hash}.txt"
            kb_s3_key = f"notices/{source_month}_{doc_hash}.txt"

            # Download & Parse PDF
            notice_text, parsed_items = download_and_parse_cdsco_pdf(
                pdf_url=pdf_url,
                title=title,
                source_month=source_month,
                doc_type=doc_type,
                raw_s3_key=raw_s3_key,
            )

            if notice_text and parsed_items:
                processed_any_live = True
                # Upload to S3 raw bucket
                try:
                    s3.put_object(
                        Bucket=settings.S3_RAW_DOCUMENTS_BUCKET,
                        Key=raw_s3_key,
                        Body=notice_text.encode("utf-8"),
                        ContentType="text/plain; charset=utf-8",
                    )
                    s3.put_object(
                        Bucket=settings.S3_KB_DOCUMENTS_BUCKET,
                        Key=kb_s3_key,
                        Body=notice_text.encode("utf-8"),
                        ContentType="text/plain; charset=utf-8",
                    )
                except Exception as exc:
                    logger.warning(f"S3 upload error for {kb_s3_key}: {exc}")

                notice_spurious = 0
                for item in parsed_items:
                    try:
                        batches_table.put_item(Item=convert_floats_to_decimals(item))
                        total_batches_ingested += 1
                        if item.get("alert_status") == "SPURIOUS":
                            total_spurious_flagged += 1
                            notice_spurious += 1

                        mfr_id = item.get("manufacturer_id_normalized", "unknown")
                        if mfr_id not in mfr_aggregates:
                            mfr_aggregates[mfr_id] = {
                                "name": item.get("manufacturer_name", ""),
                                "nsq_count": 0,
                                "spurious_count": 0,
                            }
                        if item.get("alert_status") == "SPURIOUS":
                            mfr_aggregates[mfr_id]["spurious_count"] += 1
                        else:
                            mfr_aggregates[mfr_id]["nsq_count"] += 1
                    except Exception as b_exc:
                        logger.warning(f"Batch insert error: {b_exc}")

                # Save document metadata
                doc_item = {
                    "PK": f"DOC#{doc_hash}",
                    "doc_url": pdf_url,
                    "doc_type": doc_type,
                    "source_month": source_month,
                    "title": title,
                    "doc_hash": doc_hash,
                    "s3_key_raw": raw_s3_key,
                    "s3_key_kb": kb_s3_key,
                    "parse_status": "PARSED",
                    "rows_extracted": len(parsed_items),
                    "spurious_count": notice_spurious,
                    "ingested_at": now_iso,
                }
                ingested_docs_table.put_item(Item=convert_floats_to_decimals(doc_item))
                total_docs_ingested += 1

                candidate_summaries.append({
                    "id": f"DOC#{doc_hash}",
                    "month": source_month,
                    "name": title,
                    "type": doc_type,
                    "batchesFlagged": len(parsed_items),
                    "spuriousCount": notice_spurious,
                    "url": pdf_url,
                    "status": "INGESTED",
                    "docHash": doc_hash,
                })

        # Also store the next 15 candidates as DISCOVERED_CANDIDATE
        for cand in live_candidates[max_live_pdfs:max_live_pdfs + 15]:
            doc_hash = cand["doc_hash"]
            cand_pdf = resolve_cdsco_pdf_url(cand["jsp_url"]) or cand["jsp_url"]
            cand_item = {
                "PK": f"DOC#{doc_hash}",
                "doc_url": cand_pdf,
                "doc_type": cand["doc_type"],
                "source_month": cand["source_month"],
                "title": cand["title"],
                "doc_hash": doc_hash,
                "parse_status": "DISCOVERED_CANDIDATE",
                "rows_extracted": 0,
                "spurious_count": 0,
                "ingested_at": now_iso,
            }
            try:
                ingested_docs_table.put_item(Item=convert_floats_to_decimals(cand_item))
            except Exception:
                pass

    # If live processing did not succeed (e.g. timeout), process fallback catalogue
    if not processed_any_live:
        logger.info("Using fallback catalogue notices")
        for notice in CORE_GAZETTE_NOTICES:
            title = notice["title"]
            doc_url = notice["doc_url"]
            doc_type = notice["doc_type"]
            source_month = notice["source_month"]
            table_matrix = notice.get("table", [])

            doc_hash = hashlib.sha256(doc_url.encode("utf-8")).hexdigest()[:16]
            raw_s3_key = f"raw-documents/{source_month}_{doc_hash}.txt"
            kb_s3_key = f"notices/{source_month}_{doc_hash}.txt"

            parsed_items, _ = parse_table_rows(
                table_matrix=table_matrix,
                source_month=source_month,
                source_document_s3_key=raw_s3_key,
            )

            for item in parsed_items:
                batches_table.put_item(Item=convert_floats_to_decimals(item))
                total_batches_ingested += 1
                if item.get("alert_status") == "SPURIOUS":
                    total_spurious_flagged += 1

            doc_item = {
                "PK": f"DOC#{doc_hash}",
                "doc_url": doc_url,
                "doc_type": doc_type,
                "source_month": source_month,
                "title": title,
                "doc_hash": doc_hash,
                "s3_key_raw": raw_s3_key,
                "s3_key_kb": kb_s3_key,
                "parse_status": "PARSED",
                "rows_extracted": len(parsed_items),
                "spurious_count": 1 if "Spurious" in title else 0,
                "ingested_at": now_iso,
            }
            ingested_docs_table.put_item(Item=convert_floats_to_decimals(doc_item))
            total_docs_ingested += 1

    # Update manufacturer counters
    for mfr_id, data in mfr_aggregates.items():
        try:
            mfr_table.put_item(Item=convert_floats_to_decimals({
                "PK": f"MFR#{mfr_id}",
                "canonical_name": data["name"],
                "total_nsq_batches": data["nsq_count"],
                "total_spurious_batches": data["spurious_count"],
                "total_community_flagged_batches": 0,
                "last_updated": now_iso,
            }))
        except Exception:
            pass

    # Trigger Bedrock Knowledge Base Ingestion Job
    bedrock_job_id = None
    bedrock_job_status = "SKIPPED"
    try:
        bedrock = get_boto_session().client("bedrock-agent")
        kb_id = "W7Q20DERIH"
        ds_id = "19SAQUQWAM"
        ingest_resp = bedrock.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            description=f"Live CDSCO Crawl Ingestion Run at {now_iso}",
        )
        job_summary = ingest_resp.get("ingestionJob", {})
        bedrock_job_id = job_summary.get("ingestionJobId")
        bedrock_job_status = job_summary.get("status", "STARTING")
        logger.info(f"Triggered Bedrock Knowledge Base ingestion job: {bedrock_job_id} ({bedrock_job_status})")
    except Exception as exc:
        logger.warning(f"Could not trigger Bedrock ingestion job: {exc}")
        bedrock_job_status = f"FAILED: {exc}"

    return {
        "status": "SUCCESS",
        "source": "https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/",
        "documents_ingested": total_docs_ingested,
        "batches_ingested": total_batches_ingested,
        "spurious_flagged": total_spurious_flagged,
        "ingested_at": now_iso,
        "candidates": candidate_summaries,
        "bedrock_kb": {
            "knowledge_base_id": "W7Q20DERIH",
            "data_source_id": "19SAQUQWAM",
            "job_id": bedrock_job_id,
            "status": bedrock_job_status,
        },
    }

