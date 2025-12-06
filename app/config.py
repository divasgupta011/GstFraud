# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_env: str = "dev"

    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str

    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    
    # Groq / LangChain LLM
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"  # or any Groq-supported chat model


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
