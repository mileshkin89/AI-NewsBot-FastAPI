"""
SimHash-based deduplication service for news items.

Checks duplicates only within the configured lookback window (SIMHASH_DEDUP_LOOKBACK_HOURS).
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import NewsItem
from apps.news_deduplicator.text_normalizer import normalize_text
from apps.news_deduplicator.simhash import compute_simhash, hamming_distance
from logging_config import get_logger
from settings import settings

logger = get_logger(__name__)


class SimhashDeduplicator:
    """Deduplicate news by SimHash (64-bit) over the configured lookback window."""

    async def check_duplicate(
        self,
        db_session: AsyncSession,
        text: str,
        threshold: int = 3,
        title: Optional[str] = None,
        current_item_id: Optional[int] = None,
    ) -> tuple[bool, Optional[int], int]:
        """
        Check if text is a duplicate of an existing news item in the lookback window.

        Never returns current_item_id as duplicate_of (excludes current row from search).

        Args:
            db_session: Async DB session.
            text: Full news text (raw_text).
            threshold: Max Hamming distance to consider duplicate (default 3).
            title: Optional title for early-exit when text is short (exact match).
            current_item_id: Id of the item being checked; excluded from candidates.

        Returns:
            Tuple (is_duplicate, existing_news_id or None, simhash).
        """
        normalized = normalize_text(text or "")
        simhash = compute_simhash(normalized)

        # Early exit: short text → fallback to title exact match
        if len(normalized) < 100 and title is not None:
            existing_id = await self._find_by_title_exact(db_session, title, exclude_id=current_item_id)
            if existing_id is not None:
                logger.debug(
                    f"Short text fallback: title exact match, duplicate_of_id={existing_id}"
                )
                return True, existing_id, simhash
            return False, None, simhash

        # Load last N hours: only id and simhash (only already-processed items have simhash set)
        # Exclude current item so we never set duplicate_of_id = self
        since = datetime.now(timezone.utc) - timedelta(hours=settings.SIMHASH_DEDUP_LOOKBACK_HOURS)
        conditions = [
            NewsItem.created_at >= since,
            NewsItem.simhash.isnot(None),
        ]
        if current_item_id is not None:
            conditions.append(NewsItem.id != current_item_id)
        stmt = select(NewsItem.id, NewsItem.simhash).where(*conditions)
        result = await db_session.execute(stmt)
        rows = result.all()

        for row in rows:
            existing_id, existing_simhash = row[0], row[1]
            distance = hamming_distance(simhash, existing_simhash)
            if distance <= threshold:
                logger.info(
                    f"SimHash duplicate: distance={distance}, duplicate_of_id={existing_id}, simhash={simhash}"
                )
                return True, existing_id, simhash

        return False, None, simhash

    async def _find_by_title_exact(
        self,
        db_session: AsyncSession,
        title: str,
        exclude_id: Optional[int] = None,
    ) -> Optional[int]:
        """Find a news item with the same title in the lookback window; return first id or None."""
        if not title or not title.strip():
            return None
        since = datetime.now(timezone.utc) - timedelta(hours=settings.SIMHASH_DEDUP_LOOKBACK_HOURS)
        conditions = [
            NewsItem.created_at >= since,
            NewsItem.title == title.strip(),
        ]
        if exclude_id is not None:
            conditions.append(NewsItem.id != exclude_id)
        stmt = select(NewsItem.id).where(*conditions).limit(1)
        result = await db_session.execute(stmt)
        row = result.first()
        return row[0] if row else None
