from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    # Parser settings
    TG_API_ID: int
    TG_API_HASH: str
    TG_SESSION_NAME: str
    TG_SESSION_DIR: Path = str(BASE_DIR / "sessions")
    NEWS_PARSE_LIMIT: int = 10

    # OpenAI  settings
    OPENAI_API_KEY: str
    OPENAI_API_MODEL: str = "gpt-3.5-turbo"  # "gpt-4.1-mini"
    OPENAI_API_MODEL_TEMPERATURE: float = 0.3

    TG_TOKEN: str

    # Postgresql settings
    POSTGRES_DB: str
    POSTGRES_DB_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str

    # Data: CSV files in the data directory
    SOURCES_CSV_PATH: Path = BASE_DIR / "data" / "sources.csv"
    CATEGORIES_CSV_PATH: Path = BASE_DIR / "data" / "categories.csv"

    # Path to application logs
    PATH_TO_LOGS: Path = BASE_DIR / "logs"

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def TG_SESSION_PATH(self) -> str:
        return str(self.TG_SESSION_DIR / self.TG_SESSION_NAME)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        """Return full Redis connection URL."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()
