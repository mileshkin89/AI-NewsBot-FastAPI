"""Post text generation via OpenAI and orchestration of pending posts."""
from logging_config import get_logger

from apps.post_generator.prompt_loader import get_prompts
from infrastructure.openai_llm import OpenAILLMClient, get_open_ai_llm_client
from database.repository import NewsRepository

logger = get_logger(__name__)


async def get_post_generator() -> 'PostGenerator':
    """Return a PostGenerator wired to the shared OpenAI client."""
    client: OpenAILLMClient = get_open_ai_llm_client
    return PostGenerator(client)


class PostGenerator:
    """Generate post text from raw news using OpenAI."""

    def __init__(self, client: OpenAILLMClient):
        """Initialize with the OpenAI client used for completion."""
        self.client: OpenAILLMClient = client

    async def generate_text(
            self,
            input_text: str,
            prompt: str | None = None,
            system_prompt: str | None = None,
            max_output_tokens: int = 800,
    ) -> str:
        """
        Generate post text from raw input and a prompt.

        Args:
            input_text: Raw source text (e.g. parsed news).
            prompt: Instruction for generation (rewrite, summarize, etc.).
            system_prompt: Optional system-level instructions.
            max_output_tokens: Maximum length of generated text.

        Returns:
            Generated text.
        """
        sys_prompt, usr_prompt = get_prompts()
        prompt = prompt if prompt is not None else usr_prompt
        system_prompt = system_prompt if system_prompt is not None else sys_prompt

        user_content = (
            f"PROMPT:\n{prompt}\n\n"
            f"INPUT TEXT:\n{input_text}"
        )

        response = await self.client.create_response(
            max_output_tokens=max_output_tokens,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )

        return response.output_text.strip()


class PostGenerationService:
    """
    Orchestrate post text generation.

    Load pending posts from the repo, generate text via the given generator,
    and persist results back.
    """

    def __init__(self, repo: NewsRepository, generator: PostGenerator):
        """
        Initialize with repository and generator.

        Args:
            repo: Repository for loading pending posts and saving results.
            generator: Text generator (e.g. PostGenerator) for raw text to post text.
        """
        self._repo = repo
        self._generator = generator

    async def process_pending_posts(self) -> None:
        """Fetch posts with status NEW, generate text for each, save and set status GENERATED."""
        pending = await self._repo.get_posts_pending_generation()

        for post_id, raw_text in pending:
            try:
                text = await self._generator.generate_text(raw_text)
                await self._repo.mark_post_generated(post_id, text)
            except Exception as e:
                logger.exception("Post generation failed for post_id=%s: %s", post_id, e)
                await self._repo.mark_post_failed(post_id)
