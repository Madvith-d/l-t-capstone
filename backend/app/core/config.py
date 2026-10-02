from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    log_level: str = "INFO"
    backend_cors_origins: list[str] | str = ["http://localhost:3000"]
    database_url: str = "sqlite:///./academic_assistant.db"

    llm_provider: Literal["local", "gemini"] = "gemini"
    llm_model: str = "gemini-2.5-flash-lite"
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    llm_timeout_seconds: float = 30

    embedding_provider: Literal["local", "fastembed"] = "fastembed"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    embedding_cache_dir: str = ".cache/fastembed"

    retrieval_top_k: int = Field(5, ge=1, le=50)
    retrieval_score_threshold: float = Field(0.35, ge=0, le=1)
    chunk_size_tokens: int = Field(850, ge=100)
    chunk_overlap_tokens: int = Field(125, ge=0)
    conversation_history_limit: int = Field(12, ge=2, le=50)
    max_upload_mb: int = Field(20, ge=1, le=100)
    calendar_provider: Literal["mock"] = "mock"

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("chunk_overlap_tokens")
    @classmethod
    def overlap_is_smaller(cls, value: int, info):
        size = info.data.get("chunk_size_tokens", 850)
        if value >= size:
            raise ValueError("CHUNK_OVERLAP_TOKENS must be less than CHUNK_SIZE_TOKENS")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
