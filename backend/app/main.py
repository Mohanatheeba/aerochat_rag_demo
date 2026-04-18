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

if __name__ == "__main__":
    import uvicorn
    import os
    # This tells the app to use the port Render assigns it
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

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
