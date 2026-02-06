from apps.post_generator.prompts import SYSTEM_PROMPT, USER_PROMPT
from services.openai import OpenAIClient, get_open_ai_client


class PostGenerator:
    def __init__(self, client: OpenAIClient):
        self.client: OpenAIClient = client

    async def generate_text(
            self,
            input_text: str,
            prompt: str = USER_PROMPT,
            system_prompt: str | None = SYSTEM_PROMPT,
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


async def get_post_generator() -> PostGenerator:
    client: OpenAIClient = get_open_ai_client
    return PostGenerator(client)
