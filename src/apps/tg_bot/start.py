"""Start command handler: register user and show welcome message."""

from aiogram import Router, F
from aiogram.types import Message

from apps.tg_bot.repository import UserRepository

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message) -> None:
    """
    Handle /start: create user if new, then send welcome text and prompt to choose categories.
    """
    chat_id = message.from_user.id

    await UserRepository.create_user(chat_id)

    await message.answer(
        "Hello! You have subscribed to the newsletter.\n"
        f"Your id = {chat_id}\n"
        "Choose /categories to select news topics."
    )
