from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Entrance Gateway RAG Chatbot"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    backend_api_base_url: str = Field(
        default="https://api.entrancegateway.com/api/v1",
        alias="BACKEND_API_BASE_URL",
    )
    backend_api_page_size: int = Field(default=100, ge=1, le=500, alias="BACKEND_API_PAGE_SIZE")

    ollama_base_url: str = Field(default="http://ollama:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5:3b", min_length=1, alias="OLLAMA_MODEL")
    ollama_embed_model: str = Field(default="nomic-embed-text", min_length=1, alias="OLLAMA_EMBED_MODEL")

    chroma_host: str = Field(default="chromadb", min_length=1, alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, ge=1, le=65535, alias="CHROMA_PORT")
    chroma_collection: str = Field(default="entrance_knowledge", min_length=1, alias="CHROMA_COLLECTION")

    redis_url: str = Field(default="redis://redis:6379/0", min_length=1, alias="REDIS_URL")
    session_ttl_seconds: int = Field(default=3600, ge=60, alias="SESSION_TTL_SECONDS")

    api_key: str = Field(default="change-me-admin-api-key", min_length=16, alias="API_KEY")
    chatbot_backend_jwt: str = Field(default="", alias="CHATBOT_BACKEND_JWT")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    rate_limit_requests: int = Field(default=30, ge=1, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, ge=1, alias="RATE_LIMIT_WINDOW")
    webhook_secret: str = Field(default="", alias="WEBHOOK_SECRET")

    uvicorn_workers: int = Field(default=1, ge=1, le=2, alias="UVICORN_WORKERS")
    max_chat_history_messages: int = Field(default=5, ge=0, le=50, alias="MAX_CHAT_HISTORY_MESSAGES")
    retrieval_dense_top_k: int = Field(default=20, ge=1, le=100, alias="RETRIEVAL_DENSE_TOP_K")
    retrieval_keyword_top_k: int = Field(default=20, ge=1, le=100, alias="RETRIEVAL_KEYWORD_TOP_K")
    retrieval_final_top_k: int = Field(default=5, ge=1, le=20, alias="RETRIEVAL_FINAL_TOP_K")
    chunk_size_chars: int = Field(default=600, ge=100, le=4000, alias="CHUNK_SIZE_CHARS")
    chunk_overlap_chars: int = Field(default=120, ge=0, alias="CHUNK_OVERLAP_CHARS")

    @model_validator(mode="after")
    def validate_runtime_parameters(self) -> "Settings":
        """Validate cross-field runtime settings."""

        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError("CHUNK_OVERLAP_CHARS must be less than CHUNK_SIZE_CHARS")
        if self.retrieval_final_top_k > self.retrieval_dense_top_k + self.retrieval_keyword_top_k:
            raise ValueError(
                "RETRIEVAL_FINAL_TOP_K cannot exceed dense + keyword candidate counts"
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def chroma_base_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
