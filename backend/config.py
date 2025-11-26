from pydantic_settings import BaseSettings
from typing import Optional

class Config(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    OPENAI_API_KEY: Optional[str] = None
    EMERGENT_LLM_KEY: Optional[str] = None
    MONGO_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "tarot_bot"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

config = Config()
