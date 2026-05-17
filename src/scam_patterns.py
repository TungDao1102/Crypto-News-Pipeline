import re

from src.models import DraftContent

SCAM_KEYWORDS = [
    "pump",
    "dump",
    "get-rich-quick",
    "guaranteed",
    "double your",
    "risk-free",
    "fast profit",
    "instant profit",
    "no loss",
    "guaranteed return",
    "double your money",
    "get rich",
    "make money fast",
    "100% profit",
]


def is_suspicious(text: str) -> bool:
    lower = text.lower()
    for kw in SCAM_KEYWORDS:
        if re.search(re.escape(kw), lower):
            return True
    return False


def is_low_confidence(draft: DraftContent, used_fallback: bool) -> bool:
    if used_fallback:
        return True
    body = f"{draft.telegram_markdown} {draft.binance_square_markdown}"
    if len(body.strip()) < 100:
        return True
    sentences = [s for s in re.split(r"[.!?]+", body) if s.strip()]
    if len(sentences) < 3:
        return True
    return False
