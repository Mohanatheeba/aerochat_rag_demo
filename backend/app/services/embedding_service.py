from openai import AsyncOpenAI
from ..core.config import get_settings
from typing import List, Optional

class EmbeddingService:
    """Handles vector embedding generation using OpenAI's text-embedding-3-small."""
    
    def __init__(self):
        self.settings = get_settings()
        # The AsyncOpenAI client automatically looks for OPENAI_API_KEY if not passed,
        # but we pass it explicitly from our settings for clarity.
        self.client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
        self.model = self.settings.EMBEDDING_MODEL

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single string using OpenAI."""
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"OpenAI Embedding Error: {e}")
            raise Exception(f"Failed to generate embedding: {e}")

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of strings using OpenAI."""
        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"OpenAI Batch Embedding Error: {e}")
            raise Exception(f"Failed to generate batch embeddings: {e}")

_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
