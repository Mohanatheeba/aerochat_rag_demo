from ..core.supabase_client import get_supabase
from ..services.embedding_service import get_embedding_service
from ..core.config import get_settings
from typing import Optional, List, Dict, Tuple

class RAGRetrievalService:
    """
    Performs semantic search over indexed document chunks using PGVector (Supabase).
    """

    def __init__(self):
        self.supabase = get_supabase()
        self.embedder = get_embedding_service()
        self.settings = get_settings()
        # Import internally to avoid circular dependencies
        from ..services.llm_service import get_llm_service
        self.llm = get_llm_service()

    async def retrieve(
        self,
        tenant_id: str,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """
        Embed query and find relevant context from Supabase PGVector.
        Now includes AI Query Refinement for better understanding.
        """
        k = top_k or 8
        
        # Phase 1: AI Query Understanding
        search_query = self.llm.refine_query(query)
        print(f"🕵️  Intent Refined: '{query}' -> '{search_query}'")
        
        # Phase 2: Embedding
        query_embedding = await self.embedder.embed_text(search_query)

        # Call the RPC function defined in supabase_setup.sql
        print(f"🔍 Searching DB for tenant {tenant_id}...")
        result = self.supabase.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "p_tenant_id": tenant_id,
                "match_count": k,
                "match_threshold": 0.1
            }
        ).execute()
        
        print(f"📊 Search returned {len(result.data)} matches.")

        if not result.data:
            return []

        return [
            {
                "chunk_text": row["chunk_text"],
                "document_id": row["document_id"],
                "similarity": row.get("similarity", 0.0)
            }
            for row in result.data
        ]

    async def get_context_string(self, tenant_id: str, query: str) -> Tuple[str, List[Dict]]:
        """
        Retrieve chunks and format as context string for LLM.
        """
        chunks = await self.retrieve(tenant_id, query)

        if not chunks:
            return "", []

        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(
                f"[Source {i+1}] (relevance: {chunk['similarity']:.2f})\n{chunk['chunk_text']}"
            )

        context = "\n\n---\n\n".join(context_parts)
        return context, chunks

_retrieval_service: Optional[RAGRetrievalService] = None

def get_retrieval_service() -> RAGRetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RAGRetrievalService()
    return _retrieval_service
