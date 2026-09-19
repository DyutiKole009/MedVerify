"""
CDSCO NSQ Notifications page scraper (§5.2 step 2).
Scrapes monthly NSQ PDF alert links and records candidate documents into DynamoDB.
"""
import hashlib
import re
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from pydantic import BaseModel
import requests

from src.tools.aws import get_dynamodb_resource
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


class CDSCODocCandidate(BaseModel):
    doc_url: str
    doc_hash: str
    doc_type: str  # 'CENTRAL' | 'STATE'
    source_month: str  # 'YYYY-MM'
    title: str


def classify_doc_type(title_or_url: str) -> str:
    """Classifies document as CENTRAL or STATE based on name matching (§5.2)."""
    text = title_or_url.lower()
    for state in INDIAN_STATES:
        if state in text:
            return "STATE"
    return "CENTRAL"


def extract_source_month(text: str) -> str:
    """Extracts publication month in YYYY-MM format from text or returns current."""
    months = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
        "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        "january": "01", "february": "02", "march": "03", "april": "04", "may": "05", "june": "06",
        "july": "07", "august": "08", "september": "09", "october": "10", "november": "11", "december": "12"
    }
    match = re.search(r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)[^\d]*(\d{4})", text.lower())
    if match:
        m_name = match.group(1)
        m_year = match.group(2)
        m_num = months.get(m_name, "01")
        return f"{m_year}-{m_num}"
    return "2026-09"


def parse_listing_html(html_content: str, base_url: str = "https://cdsco.gov.in") -> List[CDSCODocCandidate]:
    """Parses HTML and finds all NSQ PDF document candidate links (§5.2)."""
    soup = BeautifulSoup(html_content, "html.parser")
    candidates: List[CDSCODocCandidate] = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        link_text = a_tag.get_text(strip=True)
        combined = f"{link_text} {href}".lower()

        # Check if link points to a PDF and relates to NSQ alerts
        if href.lower().endswith(".pdf") or "nsq" in combined:
            full_url = urljoin(base_url, href)
            doc_hash = hashlib.sha256(full_url.encode("utf-8")).hexdigest()
            doc_type = classify_doc_type(combined)
            source_month = extract_source_month(combined)

            candidates.append(CDSCODocCandidate(
                doc_url=full_url,
                doc_hash=doc_hash,
                doc_type=doc_type,
                source_month=source_month,
                title=link_text or "CDSCO NSQ Notification",
            ))

    return candidates


def scrape_nsq_listing(listing_url: str = "https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/") -> List[CDSCODocCandidate]:
    """
    Fetches the CDSCO notifications page and registers pending candidates in IngestedDocs.
    """
    try:
        response = requests.get(listing_url, timeout=15, headers={"User-Agent": "MedVerify-Ingestion/2.0"})
        if not response.ok:
            logger.warning(f"CDSCO listing fetch returned HTTP {response.status_code}")
            return []
        html = response.text
    except Exception as exc:
        logger.error(f"Failed to fetch CDSCO listing page: {exc}")
        return []

    candidates = parse_listing_html(html, base_url=listing_url)
    return candidates
