"""Telegram channel parser: fetch messages and normalize to RawNews/NewsItem."""
import re

from telethon.tl.types import Message
from telethon import errors as telethon_errors

from apps.news_parser.base import BaseParser
from apps.news_parser.schemas import RawNews, NewsItem
from infrastructure.telethon import get_telegram_client
from logging_config import get_logger

logger = get_logger(__name__)


def _normalize_channel(channel: str) -> str:
    """Leave only username: strip t.me/, https://, @."""
    s = (channel or "").strip()
    s = re.sub(r"^https?://(?:www\.)?t\.me/", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^t\.me/", "", s, flags=re.IGNORECASE)
    s = s.lstrip("@")
    return s or channel


class TelegramParser(BaseParser):
    """Parse a Telegram channel into raw news items."""

    def __init__(self, source_name: str, channel: str, limit: int = 10):
        """Initialize with source name, channel identifier, and message limit."""
        super().__init__(source_name)
        self.channel = _normalize_channel(channel)
        self.limit = limit

    async def fetch(self) -> list[RawNews]:
        client = await get_telegram_client()

        if not client.is_connected():
            await client.connect()

        try:
            messages = await client.get_messages(self.channel, limit=self.limit)
        except (
            telethon_errors.ChannelInvalidError,
            telethon_errors.ChannelPrivateError,
            telethon_errors.UsernameInvalidError,
            telethon_errors.UsernameNotOccupiedError,
            telethon_errors.ChatIdInvalidError,
        ) as e:
            logger.warning(
                "Telegram channel unreachable for source %r (channel=%r): %s",
                self.source_name,
                self.channel,
                e,
            )
            return []
        except ValueError as e:
            if "username" in str(e).lower() or "No user" in str(e):
                logger.warning(
                    "Telegram channel username not found for source %r (channel=%r): %s",
                    self.source_name,
                    self.channel,
                    e,
                )
                return []
            raise
        except telethon_errors.FloodWaitError as e:
            logger.warning(
                "Telegram rate limit for source %r (channel=%r), wait %s s: %s",
                self.source_name,
                self.channel,
                e.seconds,
                e,
            )
            return []
        except Exception as e:
            logger.exception(
                "Telegram error for source %r (channel=%r): %s",
                self.source_name,
                self.channel,
                e,
            )
            return []

        return [
            RawNews(
                title=(msg.text[:120] if msg.text else ""),
                text=(msg.text or ""),
                source=self.source_name,
                url=f"https://t.me/{self.channel}/{msg.id}",
                published_at=msg.date,
                source_message_id=msg.id,
            )
            for msg in messages
            if isinstance(msg, Message) and msg.text
        ]

    async def parse(self) -> list[NewsItem]:
        raw_items = await self.fetch()
        return [self.normalize(item) for item in raw_items]
