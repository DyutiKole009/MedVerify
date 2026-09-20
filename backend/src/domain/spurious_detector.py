"""
Spurious medicine detection algorithm (§5.2 step 5).
Categorizes alert status as SPURIOUS, NSQ, or NONE based on regulatory test failure reasons.
"""
from typing import Optional, Tuple

SPURIOUS_KEYWORDS = [
    "spurious",
    "not manufactured by",
    "fictitious manufacturer",
    "does not exist",
    "counterfeit",
    "fake",
    "misbranded and spurious",
    "non-genuine",
]


def detect_alert_status(nsq_reason: Optional[str]) -> Tuple[str, bool]:
    """
    Evaluates the regulatory reason to determine alert category.
    Returns:
        (alert_status, is_spurious)
        alert_status is one of: 'SPURIOUS', 'NSQ', 'NONE'
    """
    if not nsq_reason or not nsq_reason.strip():
        return "NONE", False

    cleaned_reason = nsq_reason.lower()

    for keyword in SPURIOUS_KEYWORDS:
        if keyword in cleaned_reason:
            return "SPURIOUS", True

    return "NSQ", False
