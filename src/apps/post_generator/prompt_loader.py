"""
Load prompts from text files at application startup.

Allows non-IT specialists to edit prompts in prompts/system.txt and prompts/user.txt
without modifying Python code.
"""

from logging_config import get_logger
from settings import settings

from .default_prompts import _DEFAULT_SYSTEM, _DEFAULT_USER

logger = get_logger(__name__)

# Loaded prompts (populated by load_prompts)
SYSTEM_PROMPT: str = ""
USER_PROMPT: str = ""


def load_prompts() -> None:
    """
    Load prompts from text files into module-level SYSTEM_PROMPT and USER_PROMPT.

    Called at application startup. Uses defaults if files are missing or unreadable.
    """
    global SYSTEM_PROMPT, USER_PROMPT
    prompts_dir = settings.PATH_TO_PROMPTS

    def _read_file(name: str, default: str) -> str:
        file_path = prompts_dir / name
        try:
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                content = content.strip()
                if content:
                    logger.info("Loaded prompt from %s", file_path)
                    return content
        except OSError as e:
            logger.warning("Could not read %s: %s. Using default.", file_path, e)
        return default.strip()

    SYSTEM_PROMPT = _read_file("system.txt", _DEFAULT_SYSTEM)
    USER_PROMPT = _read_file("user.txt", _DEFAULT_USER)


def get_prompts() -> tuple[str, str]:
    """Return (SYSTEM_PROMPT, USER_PROMPT); load from files if not yet loaded."""
    if not SYSTEM_PROMPT and not USER_PROMPT:
        load_prompts()
    return SYSTEM_PROMPT, USER_PROMPT
