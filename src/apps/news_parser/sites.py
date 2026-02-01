import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import List

from .base import BaseParser
from .schemas import RawNews


class SiteParser(BaseParser):
    def __init__(
        self,
        source_name: str,
        url: str,
        title_selector: str,
        limit: int = 10,
    ):
        super().__init__(source_name)
        self.url = url
        self.title_selector = title_selector
        self.limit = limit

    async def fetch(self) -> List[RawNews]:
        response = requests.get(self.url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        items: List[RawNews] = []

        elements = soup.select(self.title_selector)[: self.limit]

        for el in elements:
            title = el.get_text(strip=True)

            if not title:
                continue

            items.append(
                RawNews(
                    title=title,
                    text=title,
                    url=self.url,
                    source=self.source_name,
                    published_at=datetime.now(timezone.utc),
                )
            )

        return items