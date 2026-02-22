"""
Tests for SimhashDeduplicator: check_duplicate with threshold and DB interaction.
Uses the same test text pairs and threshold logic as test_simhash.py.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.news_deduplicator.simhash import compute_simhash, hamming_distance
from apps.news_deduplicator.simhash_deduplicator import SimhashDeduplicator
from apps.news_deduplicator.text_normalizer import normalize_text

from .test_simhash import (
    SIMHASH_BASE_TEXT,
    SIMHASH_PAIRS_BY_DISTANCE,
    SIMHASH_TEXT_UNIQUE,
)


@pytest.fixture
def deduplicator() -> SimhashDeduplicator:
    """Return a SimhashDeduplicator instance."""
    return SimhashDeduplicator()


def _make_session_with_simhash_rows(rows: list[tuple[int, int]]) -> AsyncMock:
    """Build a mock AsyncSession that returns given (id, simhash) rows from execute."""
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = [(row_id, simhash_val) for row_id, simhash_val in rows]
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_check_duplicate_returns_false_when_no_rows(
    deduplicator: SimhashDeduplicator,
) -> None:
    """check_duplicate returns (False, None, simhash) when DB has no candidates."""
    session = _make_session_with_simhash_rows([])
    text = SIMHASH_BASE_TEXT
    is_dup, dup_id, simhash = await deduplicator.check_duplicate(
        session, text, threshold=5, current_item_id=None
    )
    assert is_dup is False
    assert dup_id is None
    assert simhash == compute_simhash(normalize_text(text))


@pytest.mark.asyncio
async def test_check_duplicate_returns_true_when_distance_leq_threshold(
    deduplicator: SimhashDeduplicator,
) -> None:
    """check_duplicate returns (True, existing_id, simhash) when some row has distance <= threshold."""
    base_text = SIMHASH_PAIRS_BY_DISTANCE[2][0]
    variant_text = SIMHASH_PAIRS_BY_DISTANCE[2][1]
    base_hash = compute_simhash(normalize_text(base_text))
    variant_hash = compute_simhash(normalize_text(variant_text))
    assert hamming_distance(base_hash, variant_hash) == 3

    session = _make_session_with_simhash_rows([(100, variant_hash)])
    is_dup, dup_id, simhash = await deduplicator.check_duplicate(
        session, base_text, threshold=5, current_item_id=None
    )
    assert is_dup is True
    assert dup_id == 100
    assert simhash == base_hash


@pytest.mark.asyncio
async def test_check_duplicate_returns_false_when_distance_gt_threshold(
    deduplicator: SimhashDeduplicator,
) -> None:
    """check_duplicate returns (False, None, simhash) when all rows have distance > threshold."""
    base_text = SIMHASH_PAIRS_BY_DISTANCE[2][0]
    variant_text = SIMHASH_PAIRS_BY_DISTANCE[2][1]
    variant_hash = compute_simhash(normalize_text(variant_text))
    session = _make_session_with_simhash_rows([(100, variant_hash)])
    is_dup, dup_id, simhash = await deduplicator.check_duplicate(
        session, base_text, threshold=2, current_item_id=None
    )
    assert is_dup is False
    assert dup_id is None


@pytest.mark.parametrize("threshold", [1, 2, 3, 4, 5, 6, 7])
@pytest.mark.asyncio
async def test_check_duplicate_respects_threshold_for_text_pairs(
    deduplicator: SimhashDeduplicator,
    threshold: int,
) -> None:
    """For each threshold 1..7, pair with distance == threshold is duplicate; pair with distance == threshold+1 is not (when available)."""
    text_a, text_b, dist = SIMHASH_PAIRS_BY_DISTANCE[threshold - 1]
    assert dist == threshold
    hash_b = compute_simhash(normalize_text(text_b))
    session = _make_session_with_simhash_rows([(42, hash_b)])
    is_dup, dup_id, _ = await deduplicator.check_duplicate(
        session, text_a, threshold=threshold, current_item_id=None
    )
    assert is_dup is True
    assert dup_id == 42

    if threshold < 7:
        text_a_next, text_b_next, dist_next = SIMHASH_PAIRS_BY_DISTANCE[threshold]
        assert dist_next == threshold + 1
        hash_b_next = compute_simhash(normalize_text(text_b_next))
        session_no = _make_session_with_simhash_rows([(99, hash_b_next)])
        is_dup_no, dup_id_no, _ = await deduplicator.check_duplicate(
            session_no, text_a_next, threshold=threshold, current_item_id=None
        )
        assert is_dup_no is False
        assert dup_id_no is None


@pytest.mark.asyncio
async def test_check_duplicate_uses_given_threshold(
    deduplicator: SimhashDeduplicator,
) -> None:
    """check_duplicate uses the provided threshold parameter, not only settings."""
    text_a, text_b, dist = SIMHASH_PAIRS_BY_DISTANCE[4]
    assert dist == 5
    hash_b = compute_simhash(normalize_text(text_b))
    session = _make_session_with_simhash_rows([(10, hash_b)])
    is_dup_4, _, _ = await deduplicator.check_duplicate(
        session, text_a, threshold=4, current_item_id=None
    )
    assert is_dup_4 is False
    session2 = _make_session_with_simhash_rows([(10, hash_b)])
    is_dup_6, dup_id, _ = await deduplicator.check_duplicate(
        session2, text_a, threshold=6, current_item_id=None
    )
    assert is_dup_6 is True
    assert dup_id == 10


@pytest.mark.asyncio
async def test_check_duplicate_unique_text_no_false_positive(
    deduplicator: SimhashDeduplicator,
) -> None:
    """check_duplicate does not mark clearly different text as duplicate when DB has one row."""
    existing_hash = compute_simhash(normalize_text(SIMHASH_BASE_TEXT))
    session = _make_session_with_simhash_rows([(1, existing_hash)])
    is_dup, dup_id, _ = await deduplicator.check_duplicate(
        session, SIMHASH_TEXT_UNIQUE, threshold=7, current_item_id=None
    )
    assert is_dup is False
    assert dup_id is None
