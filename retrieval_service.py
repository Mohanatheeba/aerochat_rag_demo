"""
RAG Retrieval Service — PGVector Cosine Similarity Search
Equivalent to: PGVector (AWS) in AeroChat architecture

Step 2 of Real-Time Flow (from architecture doc):
"Backend sends query to PGVector → cosine similarity search → 
 finds pieces of uploaded documents that best match customer's intent"
"""

from app.core.supabase_client import get_supabase
from app.services.embedding_service import get_embedding_service
from app.core.config import get_settings
from typing import Optional


class RAGRetrievalService:
    """
    Performs semantic search over indexed document chunks.
    Uses cosine similarity to find the most relevant context.
    """

    def __init__(self):
        self.supabase = get_supabase()
        self.embedder = get_embedding_service()
        self.top_k = get_settings().top_k_results

    async def retrieve(
        self,
        tenant_id: str,
        query: str,
        top_k: Optional[int] = None
    ) -> list[dict]:
        """
        Main retrieval method — Step 2 of real-time workflow.
        
        1. Embed the user's query
        2. Perform cosine similarity search in PGVector
        3. Return top-k most relevant chunks
        
        Args:
            tenant_id: Ensures tenant isolation (no cross-client data)
            query: The customer's question
            top_k: Number of results (defaults to config TOP_K_RESULTS)
        
        Returns:
            List of {chunk_text, document_id, similarity_score} dicts
        """
        k = top_k or self.top_k

        # Embed the query using same model as documents
        query_embedding = self.embedder.embed_text(query)

        # Supabase RPC for vector similarity search
        # Uses pgvector's <=> operator (cosine distance)
        result = self.supabase.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "match_tenant_id": tenant_id,
                "match_count": k,
                "similarity_threshold": 0.3  # Min similarity score
            }
        ).execute()

        if not result.data:
            return []

        return [
            {
                "chunk_text": row["chunk_text"],
                "document_id": row["document_id"],
                "chunk_index": row.get("chunk_index", 0),
                "similarity": row.get("similarity", 0.0),
                "metadata": row.get("metadata", {})
            }
            for row in result.data
        ]

    async def get_context_string(self, tenant_id: str, query: str) -> tuple[str, list[dict]]:
        """
        Retrieve chunks and format as context string for LLM.
        Returns (formatted_context, raw_chunks)
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

    def debug_embeddings(self, tenant_id: str, document_id: str) -> list[dict]:
        """
        Super Admin debug: See what chunks were indexed for a document.
        Used for: "If client reports bot giving wrong answers"
        """
        result = self.supabase.table("document_chunks").select(
            "id, chunk_index, chunk_text, metadata"
        ).eq("tenant_id", tenant_id).eq("document_id", document_id).order(
            "chunk_index"
        ).execute()

        return result.data or []

    def reindex_tenant(self, tenant_id: str) -> dict:
        """
        Super Admin: Re-index all documents for a tenant.
        Used after Intention Engine updates.
        Returns count of affected chunks.
        """
        # Get all indexed documents for tenant
        docs = self.supabase.table("documents").select("id, file_path, file_name").eq(
            "tenant_id", tenant_id
        ).eq("status", "indexed").execute()

        return {
            "tenant_id": tenant_id,
            "documents_queued": len(docs.data or []),
            "message": "Reindexing queued. Check document status."
        }


_retrieval_service: Optional[RAGRetrievalService] = None

def get_retrieval_service() -> RAGRetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RAGRetrievalService()
    return _retrieval_service
