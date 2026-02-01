import asyncio
from dataclasses import dataclass
from typing import Optional

from apps.news_parser.factory import get_parser
from apps.news_parser.schemas import NewsItem


@dataclass(slots=True)
class SourceDTO:
    type: str
    name: str
    url: str
    enabled: bool
    title_selector: Optional[str] = None


SOURCES = [
    SourceDTO(
        type="tg",
        name="Андрій Смолій. Новини",
        url="smolii_ukraine",
        enabled=True,
    ),
    SourceDTO(
        type="tg",
        name="Creaitors. AI news",
        url="creaitors_ua",
        enabled=True,
    ),
    SourceDTO(
        type="site",
        name="Python Blog",
        url="https://blog.python.org/",
        title_selector="h3.post-title",
        enabled=True,
    ),
]


async def main():
    for source in SOURCES:
        parser = get_parser(source, limit=3)
        news_items = await parser.parse()

        for item in news_items:
            news_item = NewsItem(
                title=item.title,
                url=item.url,
                raw_text=item.raw_text,
                published_at=item.published_at,
                source=source.name,
            )

            print(news_item.raw_text)
            print("=" * 40)


if __name__ == "__main__":
    asyncio.run(main())
