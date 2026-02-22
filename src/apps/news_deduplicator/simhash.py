"""
SimHash (64-bit) implementation for news deduplication.

Uses word tokenization, token frequency as weight, SHA256 (first 8 bytes).
"""

import hashlib
import re
from collections import Counter

# Word split: non-empty sequences of letters/digits (and underscore for \w)
_WORD_PATTERN = re.compile(r"\w+", re.UNICODE)
# Mask to 64 bits so DB-stored (signed) and computed (unsigned) hashes compare correctly
_BITS64_MASK = 0xFFFF_FFFF_FFFF_FFFF


def _token_hash(token: str) -> int:
    """Return 64-bit integer from SHA256 of token (first 8 bytes, big-endian)."""
    h = hashlib.sha256(token.encode("utf-8", errors="replace")).digest()
    return int.from_bytes(h[:8], byteorder="big", signed=False)


def compute_simhash(text: str) -> int:
    """
    Compute 64-bit SimHash of text.

    Tokenization: word split. Weight of each token equals its frequency.
    Each token is hashed via SHA256; first 8 bytes form a 64-bit value.
    SimHash algorithm: for each bit position, sum weights (+1 for bit 1, -1 for bit 0),
    then set that bit to 1 if sum >= 0 else 0.

    Args:
        text: Input text (typically normalized).

    Returns:
        64-bit non-negative integer.
    """
    if not text or not text.strip():
        return 0

    tokens = _WORD_PATTERN.findall(text.lower())
    if not tokens:
        return 0

    # Token -> frequency (weight)
    weights: dict[str, int] = dict(Counter(tokens))

    # Bit vector: 64 bits, each position summed with +weight or -weight
    v = [0] * 64
    for token, weight in weights.items():
        h = _token_hash(token)
        for i in range(64):
            if (h >> i) & 1:
                v[i] += weight
            else:
                v[i] -= weight

    # SimHash: bit i = 1 if v[i] >= 0 else 0
    result = 0
    for i in range(64):
        if v[i] >= 0:
            result |= 1 << i
    return result


def hamming_distance(hash1: int, hash2: int) -> int:
    """
    Return Hamming distance between two 64-bit hashes (number of differing bits).

    Both values are masked to 64 bits so signed (from DB) and unsigned (computed) compare correctly.

    Args:
        hash1: First 64-bit SimHash (signed from DB or unsigned from compute_simhash).
        hash2: Second 64-bit SimHash.

    Returns:
        Number of bits that differ (0 to 64).
    """
    h1 = hash1 & _BITS64_MASK
    h2 = hash2 & _BITS64_MASK
    return (h1 ^ h2).bit_count()


def simhash_to_db(value: int) -> int:
    """
    Convert 64-bit SimHash (unsigned) to signed int64 for PostgreSQL BIGINT.

    Values greater than 2^63-1 are stored as negative; bit pattern is preserved for comparison.
    """
    if value <= 0x7FFF_FFFF_FFFF_FFFF:
        return value
    return value - 0x1_0000_0000_0000_0000
