from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lead Search Agent"
    database_url: str = "sqlite:///./data/lead_agent.db"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:20b-cloud"
    ollama_timeout_seconds: float = 90.0
    gmail_credentials_file: str = "credentials.json"
    gmail_token_file: str = "token.json"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
