from functools import lru_cache
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "medical-rag-api"
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/medical_rag"
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8501"
    upload_dir: str = "data/raw"
    embedding_provider: str = "local-dev"
    embedding_dimensions: int = 1536
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_api_key: str | None = None
    gemini_embedding_model: str = "gemini-embedding-001"
    llm_provider: str = "gemini"
    gemini_chat_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0
    http_proxy: str | None = None
    https_proxy: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = []
        for origin in self.cors_origins.split(","):
            normalized = origin.strip().rstrip("/")
            if normalized:
                origins.append(normalized)
        return origins


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.http_proxy:
        os.environ["HTTP_PROXY"] = settings.http_proxy
    if settings.https_proxy:
        os.environ["HTTPS_PROXY"] = settings.https_proxy
    return settings
