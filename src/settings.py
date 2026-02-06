from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    # Parser settings
    TG_API_ID: int
    TG_API_HASH: str
    TG_SESSION_NAME: str
    TG_SESSION_DIR: Path = str(BASE_DIR / "sessions")

    # OpenAI  settings
    OPENAI_API_KEY: str
    OPENAI_API_MODEL: str = "gpt-3.5-turbo"  # "gpt-4.1-mini"
    OPENAI_API_MODEL_TEMPERATURE: float = 0.3

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def TG_SESSION_PATH(self) -> str:
        return str(self.TG_SESSION_DIR / self.TG_SESSION_NAME)


settings = Settings()

