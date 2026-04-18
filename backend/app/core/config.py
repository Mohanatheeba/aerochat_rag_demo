from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str = "AeroChat RAG"
    ENVIRONMENT: str = "staging"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:5173"
    
    # Secrets
    ADMIN_SECRET: str = "aerochat-dev-secret-123"
    
    # Supabase (AWS Layer replacement)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    
    # Groq (LLM)
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    
    # Upstash (Redis / Railway Layer)
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""
    HUGGINGFACE_API_KEY: str = ""
    
    # RAG Settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 150
    VECTOR_DIMENSION: int = 384
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

@lru_cache()
def get_settings():
    return Settings()
