from aiogram.types import BotCommand, BotCommandScopeDefault

from services.tg_bot import bot


async def set_commands():
    """
    Registers a predefined list of bot commands with descriptions.

    This function configures the commands that users see when typing `/` in the chat,
    such as:
        /start     - Bot start menu

    The commands are set globally for all users using the default command scope.
    """
    commands = [
        BotCommand(command='start', description='Bot start menu'),
        ]

    await bot.set_my_commands(commands, BotCommandScopeDefault())