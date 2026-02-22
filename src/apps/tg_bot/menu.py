"""Bot command menu: register /start and /categories in Telegram UI."""

from aiogram.types import BotCommand, BotCommandScopeDefault

from infrastructure.tg_bot import bot


async def set_commands() -> None:
    """
    Register a predefined list of bot commands with descriptions.

    Configures the commands users see when typing `/` in the chat (e.g. /start, /categories).
    Commands are set globally for all users using the default command scope.
    """
    commands = [
        BotCommand(command='start', description='Bot start menu'),
        BotCommand(command='categories', description='Select news categories'),
        ]

    await bot.set_my_commands(commands, BotCommandScopeDefault())