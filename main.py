"""
AeroChat RAG — FastAPI Backend
Staging Environment | 100% Free Stack

Architecture mapping:
- FastAPI = Backend (Railway layer)
- Supabase = MySQL + S3 + PGVector (AWS layer)
- Upstash Redis = Redis (Railway layer)  
- Groq = LLM
- sentence-transformers = Embedding model (local)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.api import chat, documents, super_admin, tenants


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pre-load embedding model to avoid cold-start delay."""
    print("🚀 AeroChat RAG Backend starting...")
    settings = get_settings()
    print(f"   Environment: {settings.environment}")
    print(f"   LLM Model: {settings.llm_model}")
    print(f"   Embedding Model: {settings.embedding_model}")

    # Pre-warm embedding model
    try:
        from app.services.embedding_service import get_embedding_service
        embedder = get_embedding_service()
        embedder._load_model()
        print("   Embedding model: loaded ✓")
    except Exception as e:
        print(f"   Embedding model: failed to pre-load ({e})")

    print("✅ Backend ready!")
    yield
    print("Backend shutting down...")


app = FastAPI(
    title="AeroChat RAG API",
    description="AeroChat RAG Backend — Staging Environment (Free Stack)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for React frontend
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(super_admin.router)
app.include_router(tenants.router)


@app.get("/")
async def root():
    return {
        "service": "AeroChat RAG Backend",
        "environment": "staging",
        "status": "running",
        "docs": "/docs",
        "free_stack": {
            "llm": "Groq (llama3-70b)",
            "embeddings": "sentence-transformers (local)",
            "database": "Supabase PostgreSQL",
            "vector_db": "Supabase PGVector",
            "storage": "Supabase Storage",
            "redis": "Upstash Redis"
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok", "environment": "staging"}
