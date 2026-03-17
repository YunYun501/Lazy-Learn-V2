from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DATA_DIR: Path = Path("data")
    DESCRIPTIONS_DIR: Path = Path("data/descriptions")
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = Path("data/logs")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


async def get_deepseek_api_key() -> str:
    """Return the DeepSeek API key from SQLite settings, falling back to config."""
    from app.services.settings import SettingsStore

    store = SettingsStore(db_path=settings.DATA_DIR / "lazy_learn.db")
    await store.initialize()
    db_key = await store.get_setting("deepseek_api_key")
    return db_key if db_key else settings.DEEPSEEK_API_KEY
