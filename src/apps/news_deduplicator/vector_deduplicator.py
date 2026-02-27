"""
Semantic (vector) deduplication service for news items.

Uses OpenAI embeddings and pgvector cosine distance to find
semantically similar items within the configured lookback window.
"""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import NewsItem
from infrastructure.openai_embedding import OpenAIEmbeddingClient
from logging_config import get_logger
from settings import settings

logger = get_logger(__name__)


class VectorDeduplicator:
    """Deduplicate news by cosine similarity of embedding vectors."""

    def __init__(self, embedding_client: OpenAIEmbeddingClient):
        """
        Initialize with an embedding client.

        Args:
            embedding_client: Client for obtaining text embedding vectors.
        """
        self._embedding_client = embedding_client

    async def check_duplicate(
        self,
        db_session: AsyncSession,
        text: str,
        *,
        current_item_id: int | None = None,
        threshold: float = 0.92,
        lookback_hours: int = 48,
    ) -> tuple[bool, int | None, list[float]]:
        """
        Compute embedding and check if a semantically similar item exists.

        Args:
            db_session: Async DB session.
            text: Raw news text to embed and compare.
            current_item_id: Id of the item being checked; excluded from candidates.
            threshold: Min cosine similarity (0.0-1.0) to treat as duplicate.
            lookback_hours: Only compare against items created within this window.

        Returns:
            Tuple of (is_duplicate, duplicate_of_id or None, embedding vector).
        """
        embedding = await self._embedding_client.get_embedding(text)

        since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        conditions = [
            NewsItem.created_at >= since,
            NewsItem.embedding.isnot(None),
            NewsItem.is_duplicate.is_(False),
        ]
        if current_item_id is not None:
            conditions.append(NewsItem.id != current_item_id)

        cosine_distance = NewsItem.embedding.cosine_distance(embedding)

        stmt = (
            select(NewsItem.id, cosine_distance.label("distance"))
            .where(*conditions)
            .order_by(cosine_distance)
            .limit(1)
        )
        result = await db_session.execute(stmt)
        row = result.first()

        if row is not None:
            nearest_id, distance = row[0], row[1]
            similarity = 1.0 - distance
            if similarity >= threshold:
                logger.info(
                    "Vector duplicate found: similarity=%.4f, duplicate_of_id=%s",
                    similarity,
                    nearest_id,
                )
                return True, nearest_id, embedding

        return False, None, embedding
