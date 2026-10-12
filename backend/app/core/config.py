from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Document Search"
    environment: str = "development"
    secret_key: str = "development-only-change-me"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    max_upload_mb: int = 20
    max_pdf_pages: int = 500
    max_pdf_text_chars: int = 5_000_000
    upload_dir: Path = Path("uploads")
    rate_limit_per_minute: int = 30
    database_url: str = "sqlite:///./ai_document_search.db"
    qdrant_url: str | None = None
    qdrant_collection: str = "verity_chunks"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    retrieval_top_k: int = 8
    minimum_relevance_score: float = 0.12
    chunk_size: int = 900
    chunk_overlap: int = 140
    llm_provider: Literal["extractive"] = "extractive"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_timeout_seconds: int = 30

    @field_validator("secret_key")
    @classmethod
    def secure_production_secret(cls, value: str, info):
        return value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

