
from telethon.tl.types import Message
from apps.news_parser.base import BaseParser
from apps.news_parser.schemas import RawNews, NewsItem
from infrastructure.telethon import get_telegram_client


class TelegramParser(BaseParser):
    def __init__(self, source_name: str, channel: str, limit: int = 10):
        super().__init__(source_name)
        self.channel = channel
        self.limit = limit

    async def fetch(self) -> list[RawNews]:
        client = await get_telegram_client()

        if not client.is_connected():
            await client.connect()

        messages = await client.get_messages(self.channel, limit=self.limit)

        return [
            RawNews(
                title=(msg.text[:120] if msg.text else ""),
                text=(msg.text or ""),
                source=self.source_name,
                url=f"https://t.me/{self.channel}/{msg.id}",
                published_at=msg.date,
            )
            for msg in messages
            if isinstance(msg, Message) and msg.text
        ]

    async def parse(self) -> list[NewsItem]:
        raw_items = await self.fetch()
        return [self.normalize(item) for item in raw_items]