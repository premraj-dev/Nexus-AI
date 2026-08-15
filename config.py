import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "llama3.2:3b")
    MAX_ROUNDS: int = 3
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
