"""
Unit tests for SimHash (compute_simhash, hamming_distance, simhash_to_db).

Include threshold-based duplicate detection using test text pairs for distances 1–7.
"""

import pytest

from apps.news_deduplicator.simhash import (
    compute_simhash,
    hamming_distance,
    simhash_to_db,
)
from apps.news_deduplicator.text_normalizer import normalize_text


# ---------------------------------------------------------------------------
# Base text and variants: built so that (base, variant) have Hamming distances
# 1, 2, 3, 4, 5, 6, 7 (validated empirically).
# ---------------------------------------------------------------------------

SIMHASH_BASE_TEXT = (
    "The quick brown fox jumps over the lazy dog. "
    "This sentence contains every letter of the alphabet. "
    "News today the government announced a new policy. "
    "The policy will affect millions of citizens. "
    "Experts say the change is significant and will be remembered for years."
)


def _variant(base: str, replacements: list[tuple[int, str]]) -> str:
    """Build variant by replacing words at indices. Words are split by whitespace."""
    words = base.split()
    out = words.copy()
    for idx, new_word in replacements:
        if 0 <= idx < len(out):
            out[idx] = new_word
    return " ".join(out)


# (list of (word_index, replacement)) -> yields Hamming distance 1..7
_VARIANTS_FOR_DISTANCE = {
    1: [(10, "X")],
    2: [(0, "X")],
    3: [(1, "A"), (2, "B"), (3, "C")],
    4: [(0, "Z"), (1, "Q"), (3, "W")],
    5: [(0, "Z"), (1, "Q"), (2, "X")],
    6: [(24, "Z"), (25, "Q"), (26, "X")],
    7: [(3, "A"), (4, "B"), (5, "C"), (6, "D"), (7, "E")],
}

# Precomputed (base, variant) pairs with expected distance.
SIMHASH_PAIRS_BY_DISTANCE = [
    (SIMHASH_BASE_TEXT, _variant(SIMHASH_BASE_TEXT, _VARIANTS_FOR_DISTANCE[d]), d)
    for d in [1, 2, 3, 4, 5, 6, 7]
]

# Clearly different text (distance > 7).
SIMHASH_TEXT_UNIQUE = (
    "Completely different story. Weather is fine today. Nothing to see here."
)


def _measured_distance(text_a: str, text_b: str) -> int:
    """Return Hamming distance between SimHashes of normalized text_a and text_b."""
    h1 = compute_simhash(normalize_text(text_a))
    h2 = compute_simhash(normalize_text(text_b))
    return hamming_distance(h1, h2)


# ----- Unit tests: compute_simhash -----


def test_compute_simhash_empty_returns_zero() -> None:
    """compute_simhash returns 0 for empty or whitespace-only text."""
    assert compute_simhash("") == 0
    assert compute_simhash("   ") == 0
    assert compute_simhash("\n\t") == 0


def test_compute_simhash_deterministic() -> None:
    """compute_simhash returns the same value for the same input."""
    text = "Hello world news article content here."
    assert compute_simhash(text) == compute_simhash(text)
    assert compute_simhash(text.upper()) == compute_simhash(text.lower())


def test_compute_simhash_different_texts_different_hash() -> None:
    """compute_simhash returns different values for clearly different texts."""
    h1 = compute_simhash("First unique article content.")
    h2 = compute_simhash("Second completely different story.")
    assert h1 != h2


def test_compute_simhash_non_negative_64bit() -> None:
    """compute_simhash returns a non-negative integer fitting in 64 bits."""
    h = compute_simhash(SIMHASH_BASE_TEXT)
    assert isinstance(h, int)
    assert 0 <= h <= 0xFFFF_FFFF_FFFF_FFFF


# ----- Unit tests: hamming_distance -----


def test_hamming_distance_identical_returns_zero() -> None:
    """hamming_distance returns 0 when hashes are equal."""
    h = compute_simhash("Some text")
    assert hamming_distance(h, h) == 0


def test_hamming_distance_symmetric() -> None:
    """hamming_distance is symmetric in both arguments."""
    h1 = compute_simhash("Text one")
    h2 = compute_simhash("Text two")
    assert hamming_distance(h1, h2) == hamming_distance(h2, h1)


def test_hamming_distance_range() -> None:
    """hamming_distance returns a value between 0 and 64 for any two hashes."""
    h1 = compute_simhash("Alpha")
    h2 = compute_simhash("Beta")
    d = hamming_distance(h1, h2)
    assert 0 <= d <= 64


def test_hamming_distance_masked_64bit() -> None:
    """hamming_distance correctly masks to 64 bits (signed DB value vs unsigned)."""
    h = compute_simhash(SIMHASH_BASE_TEXT)
    h_signed = simhash_to_db(h)
    assert hamming_distance(h, h_signed) == 0
    assert hamming_distance(h_signed, h) == 0


# ----- Unit tests: simhash_to_db -----


def test_simhash_to_db_small_value_unchanged() -> None:
    """simhash_to_db leaves values <= 2^63-1 unchanged."""
    v = 0x7FFF_FFFF_FFFF_FFFF
    assert simhash_to_db(v) == v
    assert simhash_to_db(0) == 0


def test_simhash_to_db_large_value_converted_to_signed() -> None:
    """simhash_to_db converts values > 2^63-1 to negative int64 (bit pattern preserved)."""
    v = 0x8000_0000_0000_0000
    out = simhash_to_db(v)
    assert out < 0
    assert (out & 0xFFFF_FFFF_FFFF_FFFF) == (v & 0xFFFF_FFFF_FFFF_FFFF)


# ----- Test text pairs: assert expected distances -----


def test_simhash_pairs_have_expected_distances() -> None:
    """Predefined (base, variant) pairs have the expected Hamming distances 1..7."""
    for text_a, text_b, expected_dist in SIMHASH_PAIRS_BY_DISTANCE:
        actual = _measured_distance(text_a, text_b)
        assert actual == expected_dist, (
            f"Expected distance {expected_dist}, got {actual}"
        )


def test_simhash_base_vs_unique_distance_above_seven() -> None:
    """Base text and clearly different text have Hamming distance greater than 7."""
    d = _measured_distance(SIMHASH_BASE_TEXT, SIMHASH_TEXT_UNIQUE)
    assert d > 7, f"Expected distance > 7, got {d}"


# ----- Threshold-based duplicate detection (threshold 1..7) -----


@pytest.mark.parametrize("threshold", [1, 2, 3, 4, 5, 6, 7])
def test_simhash_duplicate_for_threshold_when_distance_leq_threshold(
    threshold: int,
) -> None:
    """For each threshold 1..7, a pair with distance == threshold is a duplicate."""
    text_a, text_b, distance = SIMHASH_PAIRS_BY_DISTANCE[threshold - 1]
    assert distance == threshold
    h1 = compute_simhash(normalize_text(text_a))
    h2 = compute_simhash(normalize_text(text_b))
    actual_distance = hamming_distance(h1, h2)
    assert actual_distance == distance
    is_duplicate = actual_distance <= threshold
    assert is_duplicate, (
        f"Threshold {threshold}, distance {actual_distance}: should be duplicate"
    )


@pytest.mark.parametrize("threshold", [1, 2, 3, 4, 5, 6, 7])
def test_simhash_not_duplicate_for_threshold_when_distance_gt_threshold(
    threshold: int,
) -> None:
    """For each threshold 1..7, a pair with distance == threshold+1 is not a duplicate (when threshold < 7)."""
    if threshold >= 7:
        pytest.skip("No pair with distance 8 in our set; use base vs unique.")
    text_a, text_b, distance = SIMHASH_PAIRS_BY_DISTANCE[threshold]
    assert distance == threshold + 1
    h1 = compute_simhash(normalize_text(text_a))
    h2 = compute_simhash(normalize_text(text_b))
    actual_distance = hamming_distance(h1, h2)
    assert actual_distance == distance
    is_duplicate = actual_distance <= threshold
    assert not is_duplicate, (
        f"Threshold {threshold}, distance {actual_distance}: should not be duplicate"
    )


def test_simhash_threshold_zero_exact_match_only() -> None:
    """When threshold is 0, only identical texts are duplicates."""
    h = compute_simhash(normalize_text(SIMHASH_BASE_TEXT))
    assert hamming_distance(h, h) <= 0


def test_simhash_threshold_seven_base_vs_unique_not_duplicate() -> None:
    """Base text vs unique text is not a duplicate even for threshold 7."""
    h1 = compute_simhash(normalize_text(SIMHASH_BASE_TEXT))
    h2 = compute_simhash(normalize_text(SIMHASH_TEXT_UNIQUE))
    d = hamming_distance(h1, h2)
    assert d > 7
    assert not (d <= 7)
