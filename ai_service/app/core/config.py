import os


def get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    return value.strip()


def get_csv_env(name: str, default: str = "") -> list[str]:
    raw = get_env(name, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    app_name: str = get_env("AI_APP_NAME", "AI Service")
    app_version: str = get_env("AI_APP_VERSION", "1.0.0")
    cors_allowed_origins: list[str] = get_csv_env(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    qdrant_url: str = get_env("QDRANT_URL", "http://qdrant:6333")
    qdrant_api_key: str | None = get_env("QDRANT_API_KEY", "")
    qdrant_collection: str = get_env("QDRANT_COLLECTION", "route_docs")
    qdrant_distance: str = get_env("QDRANT_DISTANCE", "cosine").lower()

    embedding_provider: str = get_env("EMBEDDING_PROVIDER", "hash")
    embedding_dim: int = int(get_env("EMBEDDING_DIM", "384"))
    huggingface_api_key: str | None = get_env("HUGGINGFACE_API_KEY", "")
    hf_embedding_model: str = get_env("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    hf_llm_model: str = get_env("HF_LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    llm_provider: str = get_env("LLM_PROVIDER", "huggingface").lower()
    llm_timeout_seconds: float = float(get_env("LLM_TIMEOUT_SECONDS", "25"))
    groq_api_key: str | None = get_env("GROQ_API_KEY", "")
    groq_llm_model: str = get_env("GROQ_LLM_MODEL", "llama-3.1-8b-instant")

    chunk_size: int = int(get_env("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(get_env("CHUNK_OVERLAP", "120"))
    rag_top_k: int = int(get_env("RAG_TOP_K", "5"))
    rag_max_context_chars: int = int(get_env("RAG_MAX_CONTEXT_CHARS", "5000"))
    rag_temperature: float = float(get_env("RAG_TEMPERATURE", "0.2"))
    rag_max_new_tokens: int = int(get_env("RAG_MAX_NEW_TOKENS", "400"))

    auth_jwt_secret: str | None = get_env("AUTH_JWT_SECRET", "")
    auth_jwt_algorithm: str = get_env("AUTH_JWT_ALGORITHM", "HS256")
    auth_jwt_issuer: str | None = get_env("AUTH_JWT_ISSUER", "")
    auth_jwt_audience: str | None = get_env("AUTH_JWT_AUDIENCE", "")
    auth_internal_token_secret: str | None = get_env("AUTH_INTERNAL_TOKEN_SECRET", "")
    auth_internal_token_algorithm: str = get_env("AUTH_INTERNAL_TOKEN_ALGORITHM", "HS256")
    auth_internal_token_issuer: str | None = get_env("AUTH_INTERNAL_TOKEN_ISSUER", "core_service")
    auth_internal_token_audience: str | None = get_env("AUTH_INTERNAL_TOKEN_AUDIENCE", "ai_service_internal")
    auth_internal_allowed_services: set[str] = {
        value.strip()
        for value in (get_env("AUTH_INTERNAL_ALLOWED_SERVICES", "core_service") or "").split(",")
        if value.strip()
    }

    core_auth_me_url: str | None = get_env("CORE_AUTH_ME_URL", "http://backend:8000/api/auth/me/")
    auth_permissions_from_core: bool = get_env("AUTH_PERMISSIONS_FROM_CORE", "true").lower() == "true"
    auth_permissions_cache_seconds: int = int(get_env("AUTH_PERMISSIONS_CACHE_SECONDS", "60"))
    auth_core_timeout_seconds: float = float(get_env("AUTH_CORE_TIMEOUT_SECONDS", "3"))

    authz_strict: bool = get_env("AUTHZ_STRICT", "false").lower() == "true"
    auth_role_fallback_enabled: bool = get_env("AUTH_ROLE_FALLBACK_ENABLED", "true").lower() == "true"

    celery_broker_url: str = get_env("CELERY_BROKER_URL", "redis://redis:6379/2")
    celery_result_backend: str = get_env("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
    celery_result_expires_seconds: int = int(get_env("CELERY_RESULT_EXPIRES_SECONDS", "3600"))
    job_registry_ttl_seconds: int = int(get_env("JOB_REGISTRY_TTL_SECONDS", "7200"))

    @property
    def has_qdrant_api_key(self) -> bool:
        return bool(self.qdrant_api_key)

    @property
    def has_huggingface_key(self) -> bool:
        return bool(self.huggingface_api_key)

    @property
    def has_groq_key(self) -> bool:
        return bool(self.groq_api_key)


settings = Settings()
