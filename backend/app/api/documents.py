from fastapi import APIRouter, HTTPException, UploadFile, File, Query, BackgroundTasks
from ..services.ingestion_service import get_ingestion_service
from ..core.supabase_client import get_supabase

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload")
async def upload_document(
    tenant_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    ingestor = get_ingestion_service()
    try:
        content = await file.read()
        
        # Start ingestion in the background
        # Note: We don't await ingestion_service here anymore
        background_tasks.add_task(
            ingestor.ingest_file,
            tenant_id,
            content,
            file.filename,
            file.content_type
        )
        
        return {"status": "processing", "message": "File upload successful, indexing in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def list_documents(tenant_id: str):
    supabase = get_supabase()
    res = supabase.table("documents").select("*").eq("tenant_id", tenant_id).execute()
    return res.data

@router.delete("/{document_id}")
async def delete_document(tenant_id: str, document_id: str):
    supabase = get_supabase()
    # Cascade delete is handled by Supabase schema
    res = supabase.table("documents").delete().eq("id", document_id).eq("tenant_id", tenant_id).execute()
    return {"status": "deleted"}
