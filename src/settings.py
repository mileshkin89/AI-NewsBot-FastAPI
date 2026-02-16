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

    # Post sender settings
    TG_TOKEN: str

    # Postgresql settings
    POSTGRES_DB: str
    POSTGRES_DB_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    # Data: CSV files in the data directory
    SOURCES_CSV_PATH: Path = BASE_DIR / "data" / "sources.csv"
    CATEGORIES_CSV_PATH: Path = BASE_DIR / "data" / "categories.csv"

    # Path to application logs
    PATH_TO_LOGS: Path = BASE_DIR / "logs"
    # Path to prompts
    PATH_TO_PROMPTS: Path = BASE_DIR / "prompts"

    # Deduplicator:
    # News seen cache: TTL in days (how long "seen" items are kept per source)
    NEWS_SEEN_CACHE_TTL_DAYS: int = 30
    # SimHash dedup: look back window in hours (only items from last N hours are checked)
    SIMHASH_DEDUP_LOOKBACK_HOURS: int = 24
    # SimHash dedup: max Hamming distance (0–64) to treat two hashes as duplicate.
    # Lower = stricter (fewer duplicates, only near-identical texts). Higher = looser
    # (more items marked duplicate; more rephrasing / word changes still count as same).
    SIMHASH_DEDUP_THRESHOLD: int = 5

    PASSWORD_HASH_SCHEME: str = "argon2"

    # JWT
    SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

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
