"""Abstract base parser and common normalization for news sources."""
from abc import ABC, abstractmethod
from typing import List

from .schemas import RawNews, NewsItem


class BaseParser(ABC):
    """Abstract parser: fetch raw news and normalize to NewsItem."""

    def __init__(self, source_name: str):
        """Initialize with the source name used in normalized items."""
        self.source_name = source_name

    @abstractmethod
    async def fetch(self) -> List[RawNews]:
        """Fetch raw news items from the source."""
        raise NotImplementedError

    def normalize(self, raw: RawNews) -> NewsItem:
        """Map RawNews to NewsItem."""
        raw_text = raw.title + raw.text
        return NewsItem(
            title=raw.title,
            source=self.source_name,
            published_at=raw.published_at,
            url=raw.url,
            raw_text=raw_text,
            source_message_id=raw.source_message_id,
        )

    async def parse(self) -> List[NewsItem]:
        """Fetch raw items and return normalized NewsItem list."""
        raw_items = await self.fetch()
        return [self.normalize(item) for item in raw_items]
