"""
Documents API Routes (Knowledge Base Management)
- POST /documents/upload      → Upload + index document
- GET  /documents/            → List tenant documents
- DELETE /documents/{id}      → Delete document + vectors
- GET  /documents/{id}/chunks → Debug: view chunks (Super Admin)
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from app.services.ingestion_service import get_ingestion_service
from app.services.retrieval_service import get_retrieval_service
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/upload")
async def upload_document(
    tenant_id: str = Query(...),
    file: UploadFile = File(...)
):
    """
    Upload a document to knowledge base.
    
    Pipeline: Storage (Supabase) → Parse → Chunk → Embed → PGVector
    """
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {list(ALLOWED_TYPES.values())}"
        )

    # Read file
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    ingestion = get_ingestion_service()

    result = await ingestion.ingest_file(
        tenant_id=tenant_id,
        file_bytes=file_bytes,
        file_name=file.filename,
        mime_type=file.content_type
    )

    return {
        "success": True,
        "message": f"Document indexed with {result['chunk_count']} chunks",
        **result
    }


@router.get("/")
async def list_documents(tenant_id: str = Query(...)):
    """List all documents for a tenant."""
    supabase = get_supabase()
    result = supabase.table("documents").select(
        "id, file_name, file_size, status, chunk_count, created_at"
    ).eq("tenant_id", tenant_id).order("created_at", desc=True).execute()

    return {"documents": result.data or []}


@router.delete("/{document_id}")
async def delete_document(document_id: str, tenant_id: str = Query(...)):
    """
    Delete document, its vectors, and storage file.
    Super Admin equivalent: orphan cleanup.
    """
    ingestion = get_ingestion_service()
    success = ingestion.delete_document(tenant_id, document_id)

    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"success": True, "message": "Document and all chunks deleted"}


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    tenant_id: str = Query(...),
    is_super_admin: bool = Query(False)
):
    """
    Super Admin debug: View indexed chunks for a document.
    Used to investigate why bot is giving wrong answers.
    """
    retrieval = get_retrieval_service()
    chunks = retrieval.debug_embeddings(tenant_id, document_id)

    return {
        "document_id": document_id,
        "chunk_count": len(chunks),
        "chunks": chunks
    }


@router.post("/test-search")
async def test_vector_search(
    tenant_id: str = Query(...),
    query: str = Query(...),
    top_k: int = Query(4)
):
    """
    Test semantic search for a tenant's knowledge base.
    Returns matching chunks with similarity scores.
    """
    retrieval = get_retrieval_service()
    chunks = await retrieval.retrieve(tenant_id, query, top_k=top_k)

    return {
        "query": query,
        "results": chunks,
        "total_found": len(chunks)
    }
