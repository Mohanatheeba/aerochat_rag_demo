import torch
from sentence_transformers import SentenceTransformer
from ..core.config import get_settings
from typing import List, Optional

class EmbeddingService:
    """Handles vector embedding generation using local models."""
    
    def __init__(self):
        self.settings = get_settings()
        self.model_name = self.settings.EMBEDDING_MODEL
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model: Optional[SentenceTransformer] = None

    def _load_model(self):
        """Lazy load the model to memory."""
        if self._model is None:
            print(f"Loading embedding model: {self.model_name} on {self.device}...")
            self._model = SentenceTransformer(self.model_name, device=self.device)
            print("Model loaded successfully.")
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single string."""
        model = self._load_model()
        embedding = model.encode(text, convert_to_tensor=False)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of strings (efficient)."""
        model = self._load_model()
        embeddings = model.encode(texts, convert_to_tensor=False)
        return embeddings.tolist()

_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
