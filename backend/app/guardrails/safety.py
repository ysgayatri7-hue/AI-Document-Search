import re

from fastapi import HTTPException

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"act\s+as\s+(an?\s+)?unrestricted",
    r"override\s+(your\s+)?(policy|rules|instructions)",
    r"developer\s+message",
]
SENSITIVE_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED_PAYMENT_NUMBER]"),
]


def detect_prompt_injection(text: str) -> list[str]:
    normalized = " ".join(text.lower().split())
    return [pattern for pattern in INJECTION_PATTERNS if re.search(pattern, normalized)]


def validate_question(question: str) -> str:
    cleaned = " ".join(question.split())
    if len(cleaned) < 3 or len(cleaned) > 2000:
        raise HTTPException(422, "Question must be between 3 and 2,000 characters")
    if detect_prompt_injection(cleaned):
        raise HTTPException(400, "The question contains instruction-override language and was blocked")
    return cleaned


def sanitize_output(text: str) -> str:
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def document_is_suspicious(text: str) -> bool:
    return bool(detect_prompt_injection(text))

