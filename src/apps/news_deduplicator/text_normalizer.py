"""
Text normalization for SimHash deduplication.

Removes URLs, mentions, emoji, special characters; keeps letters and digits.
"""

import re


# URL pattern (http/https and common tlds)
_URL_PATTERN = re.compile(
    r"https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:/[^\s]*)?",
    re.IGNORECASE,
)
# @mention (word after @)
_MENTION_PATTERN = re.compile(r"@\w+")
# Emoji: main Unicode blocks (Misc Symbols, Emoticons, etc.)
_EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001F9FF\U0001F600-\U0001F64F\U0001F1E0-\U0001F1FF"
    r"\u2600-\u26FF\u2700-\u27BF\uFE00-\uFE0F\u200D]+",
    re.UNICODE,
)
# Leave only letters (any script) and digits; replace other chars with space
_LETTERS_DIGITS_ONLY = re.compile(r"[^\w\s]", re.UNICODE)
# Collapse multiple spaces/newlines into one
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """
    Normalize text for SimHash.

    Lowercase; remove URLs, @mentions, emoji, special characters; keep only
    letters and digits; collapse spaces.

    Args:
        text: Raw input text (typically 1–4096 chars).

    Returns:
        Cleaned text.
    """
    if not text or not isinstance(text, str):
        return ""

    s = text.lower().strip()
    s = _URL_PATTERN.sub(" ", s)
    s = _MENTION_PATTERN.sub(" ", s)
    s = _EMOJI_PATTERN.sub(" ", s)
    s = _LETTERS_DIGITS_ONLY.sub(" ", s)
    s = _WHITESPACE_PATTERN.sub(" ", s)
    return s.strip()
