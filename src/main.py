import asyncio

from sqlalchemy.exc import IntegrityError

from apps.news_parser.factory import get_parser
from apps.news_parser.schemas import NewsItem
from apps.post_generator.generator import get_post_generator, PostGenerator
from database.db import get_db
from database.enams import SourceType
from database.models import Source
from database.repository import get_sources


async def populate_db() -> None:
    async with get_db() as db:
        sources = [
            Source(
                type=SourceType("tg"),
                name="Андрій Смолій. Новини",
                url="smolii_ukraine",
                enabled=True,
            ),
            Source(
                type=SourceType("tg"),
                name="Creaitors. AI news",
                url="creaitors_ua",
                enabled=True,
            ),
            Source(
                type=SourceType("tg"),
                name="Алексей Руденко . Криптоинвестор",
                url="AlexRich2018",
                enabled=True,
            ),
            Source(
                type=SourceType("site"),
                name="Python Blog",
                url="https://blog.python.org/",
                title_selector="h3.post-title",
                enabled=True,
            ),
        ]

        db.add_all(sources)

        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            return


async def main():
    await populate_db()
    sources = await get_sources()

    while True:
        for source in sources:
            parser = get_parser(source, limit=1)
            news_items = await parser.parse()

            print("source: ", source.name)

            for item in news_items:
                print("item.title: ", item.title)
                news_item = NewsItem(
                    title=item.title,
                    url=item.url,
                    raw_text=item.raw_text,
                    published_at=item.published_at,
                    source=source.name,
                )

                print("news text: ", news_item.raw_text)
                print("-" * 40)

                generator: PostGenerator = await get_post_generator()

                generated_text = await generator.generate_text(news_item.raw_text)
                print("generated_text: ", generated_text)
                print("=" * 40)

        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
