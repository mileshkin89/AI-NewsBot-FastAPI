from aiogram import Bot

from services.tg_bot import bot


class PostPublisher:
    def __init__(self, chat_id: int):
        self._bot: Bot = bot
        self.chat_id: int = chat_id

    async def publish(self, text: str):
        return await self._bot.send_message(
            chat_id=self.chat_id,
            text=text,
            disable_web_page_preview=False,
        )