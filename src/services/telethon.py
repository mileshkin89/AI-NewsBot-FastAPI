from telethon import TelegramClient

from settings import settings

_client: TelegramClient | None = None


async def get_telegram_client() -> TelegramClient:
    global _client

    if _client is None:
        _client = TelegramClient(
            settings.TG_SESSION_PATH,
            settings.TG_API_ID,
            settings.TG_API_HASH,
        )

        await _client.connect()

        if not await _client.is_user_authorized():
            raise RuntimeError(
                "Telegram session is not authorized. "
                "Run telethon_login.py locally to create session."
            )

    return _client