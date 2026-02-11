from telethon import TelegramClient

from logging_config import get_logger
from settings import settings

logger = get_logger(__name__)

_client: TelegramClient | None = None


async def get_telegram_client() -> TelegramClient:
    global _client

    if _client is None:
        logger.debug("Creating Telegram client and connecting")
        _client = TelegramClient(
            settings.TG_SESSION_PATH,
            settings.TG_API_ID,
            settings.TG_API_HASH,
        )

        await _client.connect()
        logger.debug("Telegram client connected")

        if not await _client.is_user_authorized():
            logger.error(
                "Telegram session is not authorized. Run telethon_login.py locally to create session."
            )
            raise RuntimeError(
                "Telegram session is not authorized. "
                "Run telethon_login.py locally to create session."
            )

        logger.debug("Telegram client ready (session authorized)")

    logger.debug("Telegram client returned")
    return _client