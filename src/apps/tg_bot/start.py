from aiogram import Router, F
from aiogram.types import Message

from apps.tg_bot.repository import create_user

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    chat_id = message.from_user.id

    await create_user(chat_id)

    await message.answer(
        f"Hello! You have subscribed to the newsletter!\n"
        f"Your id = {chat_id}\n"
    )
