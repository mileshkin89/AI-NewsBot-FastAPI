"""
Load prompts from text files at application startup.

Allows non-IT specialists to edit prompts in prompts/system.txt and prompts/user.txt
without modifying Python code.
"""

from logging_config import get_logger
from settings import settings

logger = get_logger(__name__)

# Loaded prompts (populated by load_prompts)
SYSTEM_PROMPT: str = ""
USER_PROMPT: str = ""

# Default prompts (fallback if files are missing)
_DEFAULT_SYSTEM = """You are a professional news editor.

Your task is to transform the input text into a news post.
Write strictly in English, regardless of the source language.

Rules:
- Use only the facts contained in the input text.
- Do not add conclusions, opinions, calls to action, advertising, or emotions.
- Completely ignore the source formatting.

Formatting:
- Markdown (**, __, #, _, *, ```, etc.) is prohibited.
- The final text must not contain any Markdown tags.
- Only the following HTML tags are allowed: <b>, <i>, <u>, <s>, <code>, <pre>, <a href="...">.
- Emojis are allowed only if appropriate for a news format.

Text cleanup:
- Remove hashtags and keywords from the source (lines or fragments starting with #).
"""

_DEFAULT_USER = """Generate a news post from the input text.

Requirements:
- Title — in <b>, first line.
- After the title — two line breaks.
- Then — the main text.
- Text length 2-5 sentences.
- If the text is long, split it into logical paragraphs.
- Use emojis for better readability.
"""


def load_prompts() -> None:
    """
    Load prompts from text files into module-level SYSTEM_PROMPT and USER_PROMPT.
    Called at application startup.
    Uses defaults if files are missing or unreadable.
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
    """Return (SYSTEM_PROMPT, USER_PROMPT). Load if not yet loaded."""
    if not SYSTEM_PROMPT and not USER_PROMPT:
        load_prompts()
    return SYSTEM_PROMPT, USER_PROMPT
