"""
Embedding Service — sentence-transformers (Local, 100% FREE)
Equivalent to: AWS Bedrock / OpenAI embeddings in paid setups
Model: all-MiniLM-L6-v2 (384 dimensions, fast, accurate)

No API calls, no costs. Runs entirely on CPU.
First run downloads ~90MB model (cached after that).
"""

import numpy as np
from typing import Optional
from functools import lru_cache
from app.core.config import get_settings


class EmbeddingService:
    """
    Converts text to 384-dimensional vectors using a local model.
    These vectors are stored in Supabase PGVector.
    
    Data lifecycle (from architecture doc):
    Text → Chunks → Embeddings (this service) → PGVector storage
    """

    def __init__(self):
        self._model = None
        self.model_name = get_settings().embedding_model
        self.dimensions = 384  # all-MiniLM-L6-v2 output size

    def _load_model(self):
        """Lazy load model on first use (saves startup time)."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"[Embedding] Loading model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            print(f"[Embedding] Model loaded ✓")
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """
        Embed a single text string.
        Returns 384-dimensional vector as list of floats.
        """
        model = self._load_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple texts efficiently (batch processing).
        Used during document indexing.
        """
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=len(texts) > 10)
        return embeddings.tolist()

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors (for debugging)."""
        a, b = np.array(vec1), np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
