"""
Document Ingestion Service
Equivalent to: S3 upload + Backend parsing + PGVector indexing

Data Lifecycle (from architecture doc):
1. Upload PDF → Supabase Storage (replaces S3)
2. Parse & Chunk → Backend (this service)
3. Embed each chunk → EmbeddingService (local model)
4. Store vectors → Supabase PGVector (replaces AWS PGVector)
"""

import io
import uuid
import json
from typing import Optional
from app.core.supabase_client import get_supabase
from app.services.embedding_service import get_embedding_service
from app.core.config import get_settings


class DocumentIngestionService:
    """
    Handles the complete data lifecycle:
    PDF → Storage → Chunks → Embeddings → PGVector
    """

    BUCKET_NAME = "aerochat-media"

    def __init__(self):
        self.supabase = get_supabase()
        self.embedder = get_embedding_service()
        settings = get_settings()
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    # ─────────────────────────────────────────────────────────
    # STEP 1: Store file in Supabase Storage (replaces S3)
    # ─────────────────────────────────────────────────────────

    async def upload_to_storage(
        self,
        tenant_id: str,
        file_bytes: bytes,
        file_name: str,
        mime_type: str
    ) -> str:
        """
        Upload file to Supabase Storage.
        Path: {tenant_id}/{uuid}_{filename}
        Returns the storage path.
        """
        file_id = str(uuid.uuid4())[:8]
        storage_path = f"{tenant_id}/{file_id}_{file_name}"

        self.supabase.storage.from_(self.BUCKET_NAME).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": mime_type}
        )

        return storage_path

    # ─────────────────────────────────────────────────────────
    # STEP 2: Parse file into text
    # ─────────────────────────────────────────────────────────

    def parse_file(self, file_bytes: bytes, mime_type: str, file_name: str) -> str:
        """Extract raw text from PDF or plain text files."""
        if mime_type == "application/pdf" or file_name.endswith(".pdf"):
            return self._parse_pdf(file_bytes)
        elif mime_type in ["text/plain", "text/markdown"] or file_name.endswith((".txt", ".md")):
            return file_bytes.decode("utf-8", errors="ignore")
        elif file_name.endswith(".docx"):
            return self._parse_docx(file_bytes)
        else:
            # Try to decode as text
            return file_bytes.decode("utf-8", errors="ignore")

    def _parse_pdf(self, file_bytes: bytes) -> str:
        """Extract text from PDF using pypdf."""
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text.strip())
        return "\n\n".join(text_parts)

    def _parse_docx(self, file_bytes: bytes) -> str:
        """Extract text from Word document."""
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())

    # ─────────────────────────────────────────────────────────
    # STEP 3: Chunk text (500-1000 chars as per architecture)
    # ─────────────────────────────────────────────────────────

    def chunk_text(self, text: str) -> list[dict]:
        """
        Split text into overlapping chunks.
        Returns list of {text, index} dicts.
        """
        chunks = []
        start = 0
        index = 0
        text = text.strip()

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                for sep in ["\n\n", "\n", ". ", "! ", "? "]:
                    boundary = text.rfind(sep, start, end)
                    if boundary > start + self.chunk_size // 2:
                        end = boundary + len(sep)
                        break

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"text": chunk_text, "index": index})
                index += 1

            start = end - self.chunk_overlap
            if start >= len(text):
                break

        return chunks

    # ─────────────────────────────────────────────────────────
    # STEP 4 & 5: Embed + Store in PGVector
    # ─────────────────────────────────────────────────────────

    async def index_document(
        self,
        tenant_id: str,
        document_id: str,
        text: str
    ) -> int:
        """
        Full indexing pipeline:
        Text → Chunks → Embeddings → PGVector
        Returns number of chunks indexed.
        """
        chunks = self.chunk_text(text)
        if not chunks:
            return 0

        # Batch embed all chunks (efficient)
        texts = [c["text"] for c in chunks]
        embeddings = self.embedder.embed_batch(texts)

        # Prepare rows for bulk insert
        rows = []
        for chunk, embedding in zip(chunks, embeddings):
            rows.append({
                "tenant_id": tenant_id,
                "document_id": document_id,
                "chunk_index": chunk["index"],
                "chunk_text": chunk["text"],
                "embedding": embedding,  # Supabase handles vector serialization
                "metadata": {}
            })

        # Bulk insert into PGVector table
        self.supabase.table("document_chunks").insert(rows).execute()

        # Update document status
        self.supabase.table("documents").update({
            "status": "indexed",
            "chunk_count": len(chunks)
        }).eq("id", document_id).execute()

        return len(chunks)

    # ─────────────────────────────────────────────────────────
    # FULL PIPELINE: Upload → Parse → Index
    # ─────────────────────────────────────────────────────────

    async def ingest_file(
        self,
        tenant_id: str,
        file_bytes: bytes,
        file_name: str,
        mime_type: str
    ) -> dict:
        """
        Complete ingestion pipeline.
        Returns document record with indexing results.
        """
        # 1. Upload to Supabase Storage (S3 equivalent)
        storage_path = await self.upload_to_storage(tenant_id, file_bytes, file_name, mime_type)

        # 2. Create document record (status: processing)
        doc_result = self.supabase.table("documents").insert({
            "tenant_id": tenant_id,
            "file_name": file_name,
            "file_path": storage_path,
            "file_size": len(file_bytes),
            "mime_type": mime_type,
            "status": "processing"
        }).execute()

        document_id = doc_result.data[0]["id"]

        try:
            # 3. Parse text from file
            text = self.parse_file(file_bytes, mime_type, file_name)

            # 4 & 5. Embed and index in PGVector
            chunk_count = await self.index_document(tenant_id, document_id, text)

            # Update usage log
            self._update_usage(tenant_id, len(file_bytes), 1)

            return {
                "document_id": document_id,
                "file_name": file_name,
                "storage_path": storage_path,
                "chunk_count": chunk_count,
                "status": "indexed"
            }

        except Exception as e:
            self.supabase.table("documents").update({
                "status": "failed"
            }).eq("id", document_id).execute()
            raise e

    def _update_usage(self, tenant_id: str, file_size: int, doc_count: int):
        """Track usage for Super Admin billing audits."""
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        try:
            self.supabase.rpc("upsert_usage", {
                "p_tenant_id": tenant_id,
                "p_month": month,
                "p_doc_count": doc_count,
                "p_storage_bytes": file_size
            }).execute()
        except Exception:
            pass  # Non-critical

    def delete_document(self, tenant_id: str, document_id: str) -> bool:
        """
        Super Admin: Delete document and all its chunks (orphan cleanup).
        Also removes from Supabase Storage.
        """
        # Get document info
        doc = self.supabase.table("documents").select("*").eq("id", document_id).single().execute()
        if not doc.data:
            return False

        # Delete from storage (S3 equivalent)
        try:
            self.supabase.storage.from_(self.BUCKET_NAME).remove([doc.data["file_path"]])
        except Exception:
            pass

        # Delete chunks (cascades from documents table)
        self.supabase.table("documents").delete().eq("id", document_id).execute()
        return True


_ingestion_service: Optional[DocumentIngestionService] = None

def get_ingestion_service() -> DocumentIngestionService:
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = DocumentIngestionService()
    return _ingestion_service
