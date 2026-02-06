from openai import AsyncOpenAI

from settings import settings


class OpenAIClient:
    """
    Asynchronous client for interacting with OpenAI Assistants API.
    """

    def __init__(self, openai_api_key: str, model: str, temperature: float):
        """
        Initializes the OpenAI async client.

        Args:
            openai_api_key (str): OpenAI API key.
            model (str): Model name to use for assistant responses (e.g. "gpt-3.5-turbo").
            temperature (float): Sampling temperature for response creativity.
        """
        self._client = AsyncOpenAI(api_key=openai_api_key)
        self.model = model
        self.temperature = temperature

    async def create_response(
            self,
            *,
            input: list[dict],
            max_output_tokens: int,
    ):
        return await self._client.responses.create(
            model=self.model,
            temperature=self.temperature,
            input=input,
            max_output_tokens=max_output_tokens,
        )


get_open_ai_client = OpenAIClient(
    openai_api_key=settings.OPENAI_API_KEY,
    model=settings.OPENAI_API_MODEL,
    temperature=settings.OPENAI_API_MODEL_TEMPERATURE
)
