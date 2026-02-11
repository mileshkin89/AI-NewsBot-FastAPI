from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from logging_config import get_logger
from settings import settings

logger = get_logger(__name__)

bot = Bot(
    token=settings.TG_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()
logger.debug("Aiogram bot and dispatcher initialized")
