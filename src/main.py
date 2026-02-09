import asyncio

from apps.news_parser.factory import get_parser
from apps.news_parser.schemas import NewsItem
from apps.post_generator.generator import get_post_generator, PostGenerator

from database.repository import get_sources


async def main():
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

        await asyncio.sleep(600)


if __name__ == "__main__":
    asyncio.run(main())
