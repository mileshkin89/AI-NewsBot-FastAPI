"""
Cache of already-seen news items per source.
Checked before DB write to avoid redundant IntegrityError and DB round-trips.
"""
from __future__ import annotations

import hashlib
from typing import Any, Sequence

from redis.asyncio import Redis

KEY_PREFIX = "news_seen"
KEY_TTL_SEC = 60 * 60 * 24 * 30  # 30 days


def _fingerprint(title: str | None, raw_text: str | None, url: str) -> str:
    """Unique fingerprint: title + first 100 chars of text + url."""
    title = title or ""
    raw_text = (raw_text or "")[:100]
    url = url or ""
    payload = f"{title}:{raw_text}:{url}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_key(source_id: int) -> str:
    return f"{KEY_PREFIX}:{source_id}"


def _item_fingerprint(
    source_message_id: int | None,
    title: str | None,
    raw_text: str | None,
    url: str,
) -> str:
    """Fingerprint: channel message id (Telegram) or hash (site)."""
    if source_message_id is not None:
        return str(source_message_id)
    return _fingerprint(title, raw_text, url)


class NewsSeenCache:
    """Check and store news item fingerprints in Redis (Set per source_id)."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def is_seen(
        self,
        source_id: int,
        title: str | None,
        raw_text: str | None,
        url: str,
        source_message_id: int | None = None,
    ) -> bool:
        """True if an item with this fingerprint was already processed for this source."""
        key = _cache_key(source_id)
        fp = _item_fingerprint(source_message_id, title, raw_text, url)
        return bool(await self._redis.sismember(key, fp))

    async def mark_seen(
        self,
        source_id: int,
        title: str | None,
        raw_text: str | None,
        url: str,
        source_message_id: int | None = None,
    ) -> None:
        """Add item fingerprint to cache. TTL is set only when the key is created."""
        key = _cache_key(source_id)
        fp = _item_fingerprint(source_message_id, title, raw_text, url)
        await self._redis.sadd(key, fp)
        if await self._redis.ttl(key) == -1:
            await self._redis.expire(key, KEY_TTL_SEC)

    async def filter_unseen(
        self,
        source_id: int,
        items: Sequence[Any],
    ) -> list[Any]:
        """
        Return only items whose fingerprint is not in cache (batch via pipeline).
        Each item must have: title, raw_text, url, source_message_id (optional).
        """
        if not items:
            return []
        key = _cache_key(source_id)
        pipes: list[tuple[Any, str]] = []
        for item in items:
            fp = _item_fingerprint(
                getattr(item, "source_message_id", None),
                getattr(item, "title", None),
                getattr(item, "raw_text", None),
                getattr(item, "url", ""),
            )
            pipes.append((item, fp))
        async with self._redis.pipeline(transaction=False) as pipe:
            for _, fp in pipes:
                pipe.sismember(key, fp)
            seen_flags = await pipe.execute()
        return [item for (item, _), seen in zip(pipes, seen_flags) if not seen]

    async def mark_seen_batch(
        self,
        source_id: int,
        items: Sequence[Any],
    ) -> None:
        """
        Add fingerprints of all items to cache in one pipeline.
        Each item must have: title, raw_text, url, source_message_id (optional).
        """
        if not items:
            return
        key = _cache_key(source_id)
        fps = [
            _item_fingerprint(
                getattr(item, "source_message_id", None),
                getattr(item, "title", None),
                getattr(item, "raw_text", None),
                getattr(item, "url", ""),
            )
            for item in items
        ]
        await self._redis.sadd(key, *fps)
        if await self._redis.ttl(key) == -1:
            await self._redis.expire(key, KEY_TTL_SEC)
