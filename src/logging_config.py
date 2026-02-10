import logging
from pathlib import Path

from settings import settings


def get_logger(name: str = __name__) -> logging.Logger:
    """Creates and configures a logger with both console and file handlers.

    The logger will:
    - Output DEBUG and higher messages to the console.
    - Save WARNING and higher messages to a log file at `logs/app.log`.
    - Suppress verbose logs from `httpx` library.

    Args:
        name (str): The logger name, typically `__name__`.

    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        log_file: Path = settings.PATH_TO_LOGS / "app.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.WARNING)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        logger.setLevel(logging.DEBUG)

        logging.getLogger("httpx").setLevel(logging.WARNING)

    return logger
