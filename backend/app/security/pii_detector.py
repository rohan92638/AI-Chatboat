import re
from dataclasses import dataclass


@dataclass
class PIIResult:
    contains_pii: bool
    pii_type: str | None = None


PII_PATTERNS = [
    (
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "email",
    ),
    (
        r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b",
        "phone",
    ),
    (
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "aadhaar_like_number",
    ),
    (
        r"\b(?:\d[ -]*?){13,19}\b",
        "card_like_number",
    ),
]


def detect_pii(text: str) -> PIIResult:
    """
    Detect common PII patterns in user input.

    This is a basic application-level detector.
    It is not a complete PII detection system.
    """

    if not text:
        return PIIResult(
            contains_pii=False
        )

    for pattern, pii_type in PII_PATTERNS:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return PIIResult(
                contains_pii=True,
                pii_type=pii_type,
            )

    return PIIResult(
        contains_pii=False
    )