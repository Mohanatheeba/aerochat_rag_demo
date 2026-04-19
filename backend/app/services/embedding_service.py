import httpx
from ..core.config import get_settings
from typing import List, Optional

class EmbeddingService:
    """Handles vector embedding generation using Hugging Face Inference API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_url = f"https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
        self.headers = {"Authorization": f"Bearer {self.settings.HUGGINGFACE_API_KEY}"}

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single string via API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.api_url, 
                    headers=self.headers, 
                    json={"inputs": text},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                # Hugging Face API sometimes returns a nested list [[0.1, 0.2...]]
                # We need to make sure we return a flat list [0.1, 0.2...]
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    return data[0]
                return data
                
            except Exception as e:
                print(f"HF API Error: {e}")
                raise Exception(f"Failed to generate embedding: {e}")

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of strings via API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.api_url, 
                    headers=self.headers, 
                    json={"inputs": texts},
                    timeout=60.0
                )
                response.raise_for_status()
                # API returns a list of lists
                result = response.json()
                
                # Validation: Sometimes API might return nested list if it's a single input mistakenly
                if isinstance(result, list) and len(result) > 0:
                    return result
                
                raise Exception("Unexpected response format from HF API")
            except Exception as e:
                print(f"HF API Batch Error: {e}")
                raise Exception(f"Failed to generate batch embeddings: {e}")

_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
