"""Runtime configuration for the Agentic Graph RAG service."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.exceptions import ConfigurationError


class Settings(BaseSettings):
    """Environment-driven settings.

    Provider secrets are intentionally optional at process startup so tests,
    health checks, and readiness checks can run without paid API keys.
    Runtime provider calls validate the specific key they require.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    cohere_api_key: str | None = Field(default=None, alias="COHERE_API_KEY")
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")

    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="password123", alias="NEO4J_PASSWORD")

    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="agentic_graph_rag", alias="QDRANT_COLLECTION")

    database_url: str = Field(
        default="mysql+pymysql://rag:rag@localhost:3306/rag?charset=utf8mb4",
        alias="DATABASE_URL",
    )

    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="documents", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    session_secret: str = Field(default="change-me-in-production", alias="SESSION_SECRET")
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    session_ttl_hours: int = Field(default=168, alias="SESSION_TTL_HOURS")
    upload_max_bytes: int = Field(default=20 * 1024 * 1024, alias="UPLOAD_MAX_BYTES")

    cors_origins: str = Field(
        default="",
        alias="CORS_ORIGINS",
        description="Comma-separated allowed origins; empty means same-origin only.",
    )

    # Transactional email (Brevo HTTP API). When BREVO_API_KEY is empty the
    # sender falls back to logging the message instead of delivering it.
    brevo_api_key: str | None = Field(default=None, alias="BREVO_API_KEY")
    brevo_from_email: str = Field(default="", alias="BREVO_FROM_EMAIL")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")

    llm_provider: str = Field(default="local", alias="LLM_PROVIDER")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="gemma2:2b", alias="OLLAMA_MODEL")
    local_embedding_model: str = Field(
        default="BAAI/bge-base-en-v1.5", alias="LOCAL_EMBEDDING_MODEL"
    )
    local_request_timeout_seconds: int = Field(default=240, alias="LOCAL_REQUEST_TIMEOUT_SECONDS")

    embedding_model: str = Field(default="models/gemini-embedding-001", alias="EMBEDDING_MODEL")
    generation_model: str = Field(default="gemini-3.6-flash", alias="GENERATION_MODEL")
    evaluation_model: str = Field(default="gemini-3.5-flash-lite", alias="EVALUATION_MODEL")
    rerank_model: str = Field(default="rerank-english-v3.0", alias="RERANK_MODEL")
    embedding_dimensions: int = 768

    parent_chunk_size: int = Field(default=2000, alias="PARENT_CHUNK_SIZE")
    parent_chunk_overlap: int = Field(default=200, alias="PARENT_CHUNK_OVERLAP")
    child_chunk_size: int = Field(default=500, alias="CHILD_CHUNK_SIZE")
    child_chunk_overlap: int = Field(default=75, alias="CHILD_CHUNK_OVERLAP")

    vector_top_k: int = Field(default=12, alias="VECTOR_TOP_K")
    graph_top_k: int = Field(default=12, alias="GRAPH_TOP_K")
    rerank_top_k: int = Field(default=5, alias="RERANK_TOP_K")
    max_retries: int = Field(default=2, alias="MAX_RETRIES")
    request_timeout_seconds: int = Field(default=30, alias="REQUEST_TIMEOUT_SECONDS")

    min_relevant_documents: int = Field(default=2, alias="MIN_RELEVANT_DOCUMENTS")
    min_average_relevance: float = Field(default=0.55, alias="MIN_AVERAGE_RELEVANCE")
    min_triple_confidence: float = Field(default=0.5, alias="MIN_TRIPLE_CONFIDENCE")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator(
        "parent_chunk_size", "child_chunk_size", "vector_top_k", "graph_top_k", "rerank_top_k"
    )
    @classmethod
    def must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be positive")
        return value

    @field_validator("llm_provider")
    @classmethod
    def must_be_known_provider(cls, value: str) -> str:
        allowed = {"local", "gemini"}
        if value.lower() not in allowed:
            raise ValueError(f"llm_provider must be one of {sorted(allowed)}")
        return value.lower()

    @property
    def use_local_llm(self) -> bool:
        return self.llm_provider == "local"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def require_gemini(self) -> str:
        if not self.gemini_api_key:
            raise ConfigurationError("GEMINI_API_KEY is required for this operation")
        return self.gemini_api_key

    def require_cohere(self) -> str:
        if not self.cohere_api_key:
            raise ConfigurationError("COHERE_API_KEY is required for reranking")
        return self.cohere_api_key

    def require_tavily(self) -> str:
        if not self.tavily_api_key:
            raise ConfigurationError("TAVILY_API_KEY is required for web search")
        return self.tavily_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
