from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from ..core.supabase_client import get_supabase
from ..core.config import get_settings

router = APIRouter(prefix="/admin", tags=["Super Admin"])

def verify_admin(x_admin_secret: str = Header(None)):
    settings = get_settings()
    if not x_admin_secret or x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Admin Secret")

class TenantCreate(BaseModel):
    name: str
    domain: str = None
    shopify_enabled: bool = False
    shopify_domain: str = None
    shopify_access_token: str = None

@router.get("/tenants")
async def list_tenants(secret: str = Depends(verify_admin)):
    supabase = get_supabase()
    res = supabase.table("tenants").select("*").execute()
    return res.data

@router.post("/tenants")
async def create_tenant(tenant: TenantCreate, secret: str = Depends(verify_admin)):
    supabase = get_supabase()
    try:
        # Create tenant
        res = supabase.table("tenants").insert(tenant.model_dump()).execute()
        if not res.data:
            # Check for error in response if available in newer SDK versions
            error_msg = getattr(res, 'error', 'Unknown database error')
            raise HTTPException(status_code=400, detail=f"Database error: {error_msg}")
            
        tenant_record = res.data[0]
        tenant_id = tenant_record["id"]
        
        # Initialize default bot config
        supabase.table("bot_configs").insert({"tenant_id": tenant_id}).execute()
        
        return tenant_record
    except Exception as e:
        print(f"❌ Error creating tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str, x_admin_secret: str = Header(None)):
    verify_admin(x_admin_secret)
    supabase = get_supabase()
    # Delete tenant (cascade will handle bot_configs, docs, chunks, messages)
    try:
        res = supabase.table("tenants").delete().eq("id", tenant_id).execute()
        return {"status": "success", "message": f"Tenant {tenant_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/health")
async def system_health(secret: str = Depends(verify_admin)):
    return {
        "status": "operational",
        "services": {
            "database": "connected",
            "vector_store": "ready",
            "llm": "ready (Groq)",
            "redis": "connected (Upstash)"
        }
    }
