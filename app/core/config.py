from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str
    environment: str
    api_v1_prefix: str
    secret_key: SecretStr
    access_token_expire_minutes: int = Field(default=30, gt=0)
    database_url: str
    chroma_directory: Path = Path("./data/chroma")
    upload_directory: Path = Path("./data/uploads")
    chroma_collection_name: str = "rag_chunks"
    ollama_base_url: str
    ollama_chat_model: str
    embedding_model: str
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    redis_url: str
    cache_ttl_seconds: int = Field(default=300, ge=0)
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    chunk_size: int = Field(default=700, gt=0)
    chunk_overlap: int = Field(default=120, ge=0)
    retrieval_k: int = Field(default=5, gt=0)
    candidate_k: int = Field(default=20, gt=0)
    max_keyword_chunks: int = Field(default=5000, gt=0)
    minimum_relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    enable_query_rewriting: bool = True
    enable_query_expansion: bool = False
    query_expansion_count: int = Field(default=3, ge=1, le=8)
    enable_mmr: bool = True
    mmr_fetch_k: int = Field(default=20, gt=0)
    mmr_lambda_mult: float = Field(default=0.5, ge=0.0, le=1.0)
    enable_hybrid_search: bool = True
    enable_reranking: bool = False
    reranker_model: str
    enable_context_compression: bool = False
    context_max_chars: int = Field(default=14000, gt=0)
    history_message_limit: int = Field(default=8, ge=0)
    prompt_version: str
    insufficient_context_answer: str
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def validate_chunk_settings(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    def prepare_directories(self) -> None:
        self.chroma_directory.mkdir(parents=True, exist_ok=True)
        self.upload_directory.mkdir(parents=True, exist_ok=True)

    @property
    def signing_secret(self) -> str:
        return self.secret_key.get_secret_value()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
