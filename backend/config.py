from functools import lru_cache

from pydantic import Field
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
        default="http://api.entrancegateway.com/api/v1",
        alias="BACKEND_API_BASE_URL",
    )
    backend_api_page_size: int = Field(default=100, alias="BACKEND_API_PAGE_SIZE")

    ollama_base_url: str = Field(default="http://ollama:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5:3b", alias="OLLAMA_MODEL")
    ollama_embed_model: str = Field(default="nomic-embed-text", alias="OLLAMA_EMBED_MODEL")

    chroma_host: str = Field(default="chromadb", alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, alias="CHROMA_PORT")
    chroma_collection: str = Field(default="entrance_knowledge", alias="CHROMA_COLLECTION")

    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    session_ttl_seconds: int = Field(default=3600, alias="SESSION_TTL_SECONDS")

    api_key: str = Field(default="change-me-admin-api-key", alias="API_KEY")
    chatbot_backend_jwt: str = Field(default="", alias="CHATBOT_BACKEND_JWT")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    rate_limit_requests: int = Field(default=30, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")
    webhook_secret: str = Field(default="", alias="WEBHOOK_SECRET")

    uvicorn_workers: int = Field(default=1, alias="UVICORN_WORKERS")
    max_chat_history_messages: int = Field(default=5, alias="MAX_CHAT_HISTORY_MESSAGES")
    retrieval_dense_top_k: int = Field(default=20, alias="RETRIEVAL_DENSE_TOP_K")
    retrieval_keyword_top_k: int = Field(default=20, alias="RETRIEVAL_KEYWORD_TOP_K")
    retrieval_final_top_k: int = Field(default=5, alias="RETRIEVAL_FINAL_TOP_K")
    chunk_size_chars: int = Field(default=600, alias="CHUNK_SIZE_CHARS")
    chunk_overlap_chars: int = Field(default=120, alias="CHUNK_OVERLAP_CHARS")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def chroma_base_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
