"""
Cache of already-seen news items per source.
Checked before DB write to avoid redundant IntegrityError and DB round-trips.
"""
import hashlib

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
