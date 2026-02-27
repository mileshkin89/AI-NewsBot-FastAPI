"""OpenAI Assistants API client for post text generation."""
from openai import AsyncOpenAI, APIError, APIConnectionError, AuthenticationError, RateLimitError

from logging_config import get_logger
from settings import settings

logger = get_logger(__name__)


class OpenAILLMClient:
    """Asynchronous client for the OpenAI Assistants API."""

    def __init__(self, openai_api_key: str, model: str, temperature: float):
        """
        Initialize the OpenAI async client.

        Args:
            openai_api_key: OpenAI API key.
            model: Model name for assistant responses (e.g. "gpt-3.5-turbo").
            temperature: Sampling temperature for response creativity.
        """
        self._client = AsyncOpenAI(api_key=openai_api_key)
        self.model = model
        self.temperature = temperature
        logger.debug(f"OpenAI client initialized: model={model}, temperature={temperature}")

    async def create_response(
            self,
            *,
            input: list[dict],
            max_output_tokens: int,
    ):
        """
        Call the OpenAI Responses API and return the completion.

        Messages are passed as a list of dicts with "role" and "content" keys.
        Errors are logged and re-raised so callers can mark posts as failed or retry.

        Args:
            input: List of message dicts, e.g. [{"role": "system", "content": "..."}, ...].
            max_output_tokens: Maximum number of tokens in the generated response.

        Returns:
            The API response object; use response.output_text for the generated string.

        Raises:
            RateLimitError: When the API rate limit (429) is exceeded.
            AuthenticationError: When the API key is invalid or expired.
            APIConnectionError: On network failure or timeout.
            APIError: For other API errors (4xx/5xx).
        """
        logger.debug(f"Creating OpenAI response: model={self.model}, max_output_tokens={max_output_tokens}")
        try:
            response = await self._client.responses.create(
                model=self.model,
                temperature=self.temperature,
                input=input,
                max_output_tokens=max_output_tokens,
            )
        except RateLimitError as e:
            logger.error("OpenAI rate limit exceeded (429): %s", e)
            raise
        except AuthenticationError as e:
            logger.error("OpenAI authentication failed (invalid or expired key): %s", e)
            raise
        except APIConnectionError as e:
            logger.error("OpenAI connection error (network or timeout): %s", e)
            raise
        except APIError as e:
            logger.error("OpenAI API error: %s", e)
            raise
        logger.debug("OpenAI response created successfully")
        return response


get_open_ai_llm_client = OpenAILLMClient(
    openai_api_key=settings.OPENAI_API_KEY,
    model=settings.OPENAI_API_MODEL,
    temperature=settings.OPENAI_API_MODEL_TEMPERATURE
)
