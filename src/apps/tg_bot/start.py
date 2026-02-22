"""Start command handler: register user and show welcome message."""

from aiogram import Router, F
from aiogram.types import Message

from apps.tg_bot.repository import UserRepository
from logging_config import get_logger

logger = get_logger(__name__)

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message) -> None:
    """
    Handle /start command.

    Create user if new, then send welcome text and prompt to choose categories.
    """
    chat_id = message.from_user.id
    username = message.from_user.username

    await UserRepository.create_user(chat_id, username)

    await message.answer(
        f"Hello {username}! You have subscribed to the newsletter.\n"
        f"Your id = {chat_id}\n"
        "Choose /categories to select news topics."
    )
    logger.info(f"{username} is subscribed to newsletter.")
