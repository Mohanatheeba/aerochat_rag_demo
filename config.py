from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_key: str
    supabase_anon_key: str

    # Groq (LLM)
    groq_api_key: str
    llm_model: str = "llama3-70b-8192"

    # Upstash Redis
    upstash_redis_rest_url: str
    upstash_redis_rest_token: str

    # App
    app_secret_key: str = "change-me"
    environment: str = "staging"
    frontend_url: str = "http://localhost:5173"

    # Session
    session_ttl_seconds: int = 3600
    max_context_messages: int = 10

    # RAG
    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k_results: int = 4
    embedding_model: str = "all-MiniLM-L6-v2"

    # Shopify
    shopify_api_version: str = "2024-04"

    # Super Admin
    super_admin_email: str = "superadmin@aerochat.ai"
    super_admin_secret: str = "change-this-secret"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
