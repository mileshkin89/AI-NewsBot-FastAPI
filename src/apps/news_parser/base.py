from abc import ABC, abstractmethod
from typing import List

from .schemas import RawNews, NewsItem


class BaseParser(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    async def fetch(self) -> List[RawNews]:
        """Get raw data from the source"""
        raise NotImplementedError

    def normalize(self, raw: RawNews) -> NewsItem:
        """Mapping RawNews → NewsItem"""
        raw_text = raw.title + raw.text
        return NewsItem(
            title=raw.title,
            source=self.source_name,
            published_at=raw.published_at,
            url=raw.url,
            raw_text=raw_text,
        )

    async def parse(self) -> List[NewsItem]:
        """Get standardized data type"""
        raw_items = await self.fetch()
        return [self.normalize(item) for item in raw_items]
