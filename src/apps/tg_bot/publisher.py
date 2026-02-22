"""Publish generated posts to Telegram users."""

from aiogram import Bot

from infrastructure.tg_bot import bot


class PostPublisher:
    """Send a text message to a user's Telegram chat."""

    def __init__(self, chat_id: int):
        """
        Initialize with the recipient Telegram chat ID.

        Args:
            chat_id: Telegram chat ID of the recipient.
        """
        self._bot: Bot = bot
        self.chat_id: int = chat_id

    async def publish(self, text: str):
        """
        Send the post text to the user's chat.

        Args:
            text: Message body (may include markdown/links).

        Returns:
            The sent Message from the Telegram API.
        """
        return await self._bot.send_message(
            chat_id=self.chat_id,
            text=text,
            disable_web_page_preview=False,
        )