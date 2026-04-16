import io
import uuid
from typing import Optional, List, Dict
from ..core.supabase_client import get_supabase
from ..services.embedding_service import get_embedding_service
from ..core.config import get_settings

class DocumentIngestionService:
    """
    Handles the ingestion of documents into Supabase Storage and PGVector.
    """

    BUCKET_NAME = "aerochat_media"

    def __init__(self):
        self.supabase = get_supabase()
        self.embedder = get_embedding_service()
        self.settings = get_settings()

    async def ingest_file(
        self,
        tenant_id: str,
        file_bytes: bytes,
        file_name: str,
        mime_type: str
    ) -> Dict:
        """Upload, parse, chunk, and index a file."""
        # 1. Upload to Supabase Storage
        file_id = str(uuid.uuid4())[:8]
        storage_path = f"{tenant_id}/{file_id}_{file_name}"
        
        try:
            print(f"📦 Uploading to Supabase Storage: {storage_path}...")
            storage_res = self.supabase.storage.from_(self.BUCKET_NAME).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": mime_type}
            )
            # Check for error in response
            if hasattr(storage_res, 'error') and storage_res.error:
                 raise Exception(f"Storage Upload Failed: {storage_res.error}")
        except Exception as e:
            print(f"❌ Storage Error: {e}")
            raise Exception(f"Supabase Storage Error: Make sure the bucket '{self.BUCKET_NAME}' exists and is private. Details: {e}")

        # 2. Create document record
        try:
            doc_result = self.supabase.table("documents").insert({
                "tenant_id": tenant_id,
                "file_name": file_name,
                "file_path": storage_path,
                "file_size": len(file_bytes),
                "mime_type": mime_type,
                "status": "processing"
            }).execute()
            
            if not doc_result.data:
                raise Exception("Database insertion failed: No data returned")
                
            document_id = doc_result.data[0]["id"]
        except Exception as e:
            print(f"❌ Database Error: {e}")
            raise Exception(f"Database Error: Could not create document record. Details: {e}")

        try:
            # 3. Parse and chunk
            text = self._parse_file(file_bytes, mime_type)
            print(f"📄 Extracted {len(text)} characters of text from {file_name}")
            
            chunks = self._chunk_text(text)
            print(f"✂️  Created {len(chunks)} chunks for indexing.")
            
            # 4. Embed and store
            if chunks:
                texts = [c["text"] for c in chunks]
                embeddings = self.embedder.embed_batch(texts)
                
                rows = []
                for chunk, embedding in zip(chunks, embeddings):
                    rows.append({
                        "tenant_id": tenant_id,
                        "document_id": document_id,
                        "chunk_index": chunk["index"],
                        "chunk_text": chunk["text"],
                        "embedding": embedding
                    })
                
                print(f"💾 Storing {len(rows)} chunks into database...")
                self.supabase.table("document_chunks").insert(rows).execute()

            # Update status
            self.supabase.table("documents").update({
                "status": "indexed",
                "chunk_count": len(chunks)
            }).eq("id", document_id).execute()
            print(f"✅ Indexing complete for {file_name}")

            return {
                "id": document_id,
                "status": "indexed",
                "chunks": len(chunks)
            }

        except Exception as e:
            self.supabase.table("documents").update({"status": "failed"}).eq("id", document_id).execute()
            print(f"❌ Indexing Error: {e}")
            raise e

    def _parse_file(self, file_bytes: bytes, mime_type: str) -> str:
        if "pdf" in mime_type:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            return "\n".join([p.extract_text() for p in reader.pages])
        return file_bytes.decode("utf-8", errors="ignore")

    def _chunk_text(self, text: str) -> List[Dict]:
        chunk_size = self.settings.CHUNK_SIZE
        overlap = self.settings.CHUNK_OVERLAP
        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append({"text": text[start:end], "index": idx})
            start += (chunk_size - overlap)
            idx += 1
        return chunks

_ingestion_service: Optional[DocumentIngestionService] = None

def get_ingestion_service() -> DocumentIngestionService:
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = DocumentIngestionService()
    return _ingestion_service
