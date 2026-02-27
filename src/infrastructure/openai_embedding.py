"""OpenAI Embeddings API client for text vectorization."""
from openai import (
    AsyncOpenAI,
    APIError,
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
)

from logging_config import get_logger
from settings import settings

logger = get_logger(__name__)


class OpenAIEmbeddingClient:
    """Asynchronous client for the OpenAI Embeddings API."""

    def __init__(self, openai_api_key: str, model: str):
        """
        Initialize the embedding client.

        Args:
            openai_api_key: OpenAI API key.
            model: Embedding model name (e.g. "text-embedding-3-small").
        """
        self._client = AsyncOpenAI(api_key=openai_api_key)
        self.model = model
        logger.debug("OpenAI embedding client initialized: model=%s", model)

    async def get_embedding(self, text: str) -> list[float]:
        """
        Get embedding vector for a single text.

        Args:
            text: Input text to embed. Must be non-empty after stripping.

        Returns:
            List of floats (embedding vector) for the text.

        Raises:
            ValueError: If text is empty or only whitespace.
            RateLimitError: When the API rate limit (429) is exceeded.
            AuthenticationError: When the API key is invalid or expired.
            APIConnectionError: On network failure or timeout.
            APIError: For other API errors (4xx/5xx).
        """
        if not text or not text.strip():
            raise ValueError("text must not be empty")
        try:
            response = await self._client.embeddings.create(
                model=self.model,
                input=text.strip(),
            )
        except RateLimitError as e:
            logger.error("OpenAI embedding rate limit exceeded (429): %s", e)
            raise
        except AuthenticationError as e:
            logger.error(
                "OpenAI embedding authentication failed (invalid or expired key): %s",
                e,
            )
            raise
        except APIConnectionError as e:
            logger.error(
                "OpenAI embedding connection error (network or timeout): %s",
                e,
            )
            raise
        except APIError as e:
            logger.error("OpenAI embedding API error: %s", e)
            raise
        embedding = response.data[0].embedding
        logger.debug(
            "Embedding created: model=%s, dimensions=%s",
            self.model,
            len(embedding),
        )
        return embedding

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Get embedding vectors for multiple texts in one request.

        Args:
            texts: Non-empty list of input texts to embed.

        Returns:
            List of embedding vectors, one per input text, in the same order.

        Raises:
            ValueError: If texts is empty.
            RateLimitError: When the API rate limit (429) is exceeded.
            AuthenticationError: When the API key is invalid or expired.
            APIConnectionError: On network failure or timeout.
            APIError: For other API errors (4xx/5xx).
        """
        if not texts:
            raise ValueError("texts must not be empty")
        normalized = [t.strip() or " " for t in texts]
        try:
            response = await self._client.embeddings.create(
                model=self.model,
                input=normalized,
            )
        except RateLimitError as e:
            logger.error("OpenAI embedding rate limit exceeded (429): %s", e)
            raise
        except AuthenticationError as e:
            logger.error(
                "OpenAI embedding authentication failed (invalid or expired key): %s",
                e,
            )
            raise
        except APIConnectionError as e:
            logger.error(
                "OpenAI embedding connection error (network or timeout): %s",
                e,
            )
            raise
        except APIError as e:
            logger.error("OpenAI embedding API error: %s", e)
            raise
        # API returns data in request order
        embeddings = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        logger.debug(
            "Embeddings batch created: model=%s, count=%s, dimensions=%s",
            self.model,
            len(embeddings),
            len(embeddings[0]) if embeddings else 0,
        )
        return embeddings


get_open_ai_embedding_client = OpenAIEmbeddingClient(
    openai_api_key=settings.OPENAI_API_KEY,
    model=settings.OPENAI_EMBEDDING_MODEL,
)
