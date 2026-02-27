from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str = "sk-b7d20f3899e34d80bedcd47890ef4ca7"
    OPENAI_API_KEY: str = ""
    DATA_DIR: Path = Path("data")
    DESCRIPTIONS_DIR: Path = Path("data/descriptions")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
