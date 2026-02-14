from apps.post_generator.prompt_loader import get_prompts
from infrastructure.openai import OpenAIClient, get_open_ai_client
from database.repository import NewsRepository


async def get_post_generator() -> 'PostGenerator':
    """Return a PostGenerator wired to the shared OpenAI client."""
    client: OpenAIClient = get_open_ai_client
    return PostGenerator(client)


class PostGenerator:
    def __init__(self, client: OpenAIClient):
        self.client: OpenAIClient = client

    async def generate_text(
            self,
            input_text: str,
            prompt: str | None = None,
            system_prompt: str | None = None,
            max_output_tokens: int = 800,
    ) -> str:
        """
        Generates a news text based on raw input text and a prompt.

        Args:
            input_text (str): Raw source text (e.g. parsed news).
            prompt (str): Instruction for generation (rewrite, summarize, etc.).
            system_prompt (str | None): Optional system-level instructions.
            max_output_tokens (int): Maximum length of generated text.

        Returns:
            str: Generated text.
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
    Orchestrates post text generation: load pending posts from the repo,
    generate text via the given generator, and persist results back.
    """

    def __init__(self, repo: NewsRepository, generator: PostGenerator):
        """
        Args:
            repo: Repository for loading pending posts and saving results.
            generator: Text generator (e.g. PostGenerator) for raw text -> post text.
        """
        self._repo = repo
        self._generator = generator

    async def process_pending_posts(self) -> None:
        """Fetch posts with status NEW, generate text for each, save and set status GENERATED."""
        pending = await self._repo.get_posts_pending_generation()

        for post_id, raw_text in pending:
            text = await self._generator.generate_text(raw_text)
            await self._repo.mark_post_generated(post_id, text)
