"""
Normalization algorithms for medicine names, batch numbers, and manufacturer identifiers (§4.6).
"""
import re
from typing import Optional

# Standard corporate suffix synonym map for Indian pharmaceutical manufacturers
MANUFACTURER_SYNONYMS = {
    "private limited": "ltd",
    "pvt ltd": "ltd",
    "pvt. ltd.": "ltd",
    "pvt. ltd": "ltd",
    "limited": "ltd",
    "ltd.": "ltd",
    "pharmaceuticals": "pharma",
    "pharmaceutical": "pharma",
    "laboratories": "lab",
    "laboratory": "lab",
    "labs": "lab",
    "co.": "",
    "co": "",
    "company": "",
}


def normalize_text(text: str) -> str:
    """Standardizes general text: lowercase, remove punctuation, collapse whitespace."""
    if not text:
        return ""
    # Lowercase
    cleaned = text.lower()
    # Strip punctuation (periods, commas, parentheses, brackets, colons, semicolons)
    cleaned = re.sub(r"[.,\(\)\[\]:;\"'\\/]", " ", cleaned)
    # Collapse multiple whitespace characters into a single space and trim
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_drug_name(drug_name: Optional[str]) -> str:
    """Normalizes drug names for exact and fuzzy matching (§4.6)."""
    if not drug_name:
        return ""
    return normalize_text(drug_name)


def normalize_batch_no(batch_no: Optional[str]) -> str:
    """Normalizes batch numbers: uppercase, trims common prefixes like 'B.No', 'Batch:'."""
    if not batch_no:
        return ""
    # Strip whitespace
    cleaned = batch_no.strip().upper()
    # Remove leading common batch prefixes (e.g. 'B.NO.', 'B.NO', 'BATCH NO:', 'BNO')
    cleaned = re.sub(r"^(?:B\.?\s*NO\.?|BATCH\s*(?:NO\.?)?|BNO\.?)\s*[:#-]?\s*", "", cleaned)
    # Remove interior spaces and dashes if desired, but preserve standard alphanumeric chars
    cleaned = re.sub(r"[\s]", "", cleaned)
    return cleaned


def normalize_manufacturer_name(mfr_name: Optional[str]) -> str:
    """
    Normalizes manufacturer name applying corporate suffix synonyms (§4.6).
    Standardizes 'Pvt Ltd' -> 'ltd', 'Pharmaceuticals' -> 'pharma', etc.
    """
    if not mfr_name:
        return ""
    cleaned = normalize_text(mfr_name)

    # Word replacement using synonyms
    words = cleaned.split()
    normalized_words = []
    i = 0
    while i < len(words):
        # Check 2-word combinations (e.g. "pvt ltd", "private limited")
        if i + 1 < len(words):
            two_word = f"{words[i]} {words[i+1]}"
            if two_word in MANUFACTURER_SYNONYMS:
                replacement = MANUFACTURER_SYNONYMS[two_word]
                if replacement:
                    normalized_words.append(replacement)
                i += 2
                continue

        # Check 1-word
        word = words[i]
        if word in MANUFACTURER_SYNONYMS:
            replacement = MANUFACTURER_SYNONYMS[word]
            if replacement:
                normalized_words.append(replacement)
        else:
            normalized_words.append(word)
        i += 1

    return " ".join(normalized_words).strip()


def build_manufacturer_id(mfr_name: Optional[str]) -> str:
    """Creates a normalized partition key component for manufacturers: MFR#{id}."""
    normalized = normalize_manufacturer_name(mfr_name)
    if not normalized:
        return "UNKNOWN"
    return normalized.upper().replace(" ", "_")
