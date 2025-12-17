# backend/app/mcp_middleware.py
import re

CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

def redact_pii(text: str):
    if CARD_REGEX.search(text):
        return "[REDACTED_CARD]"
    return text

def contains_pii(text: str):
    return bool(CARD_REGEX.search(text))
