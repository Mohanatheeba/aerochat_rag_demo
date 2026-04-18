"""
AeroChat RAG — FastAPI Backend
Staging Environment | 100% Free Stack
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import get_settings
from .api import chat, documents, super_admin, tenants

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pre-load embedding model to avoid cold-start delay."""
    print("🚀 AeroChat RAG Backend starting...")
    settings = get_settings()
    
    # Backend ready
    print("✅ Backend ready!")
    yield
    print("Backend shutting down...")

app = FastAPI(
    title="AeroChat RAG API",
    description="AeroChat RAG Backend — Staging Environment (Free Stack)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for cloud and local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        "service": "AeroChat RAG API",
        "status": "ready",
        "stack": "Free (Supabase/Groq/Upstash)"
    }
