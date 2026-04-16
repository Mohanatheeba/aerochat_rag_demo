"""
Super Admin API Routes
Equivalent to: Super Admin (Railway) in AeroChat architecture

"Allows internal team to monitor system health across all client bots,
 manage billing, and manually override system settings"

- GET  /admin/tenants              → List all tenants
- POST /admin/tenants              → Create new tenant
- PUT  /admin/tenants/{id}         → Update tenant (toggle features)
- GET  /admin/tenants/{id}/usage   → Billing/usage stats
- GET  /admin/system/health        → System-wide health
- GET  /admin/redis/sessions       → Active session count (Redis monitor)
- GET  /admin/tenants/{id}/debug/vectors → Debug PGVector for a tenant
- POST /admin/tenants/{id}/reindex → Re-index all tenant vectors
- GET  /admin/support/tickets      → All support tickets
"""

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel
from typing import Optional

from app.core.supabase_client import get_supabase
from app.services.redis_session import get_redis_service
from app.services.retrieval_service import get_retrieval_service
from app.core.config import get_settings

router = APIRouter(prefix="/admin", tags=["super-admin"])


def _verify_super_admin(x_admin_secret: str = Header(...)):
    """Simple secret-based auth for Super Admin endpoints."""
    settings = get_settings()
    if x_admin_secret != settings.super_admin_secret:
        raise HTTPException(status_code=403, detail="Invalid super admin secret")
    return True


# ─────────────────────────────────────────────────────────────
# TENANT MANAGEMENT (MySQL / Supabase PostgreSQL)
# ─────────────────────────────────────────────────────────────

class CreateTenantRequest(BaseModel):
    name: str
    email: str
    plan: str = "free"


class UpdateTenantRequest(BaseModel):
    whatsapp_enabled: Optional[bool] = None
    shopify_enabled: Optional[bool] = None
    shopify_domain: Optional[str] = None
    shopify_access_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_verify_token: Optional[str] = None
    plan: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/tenants")
async def list_all_tenants(x_admin_secret: str = Header(...)):
    """List all tenants — Super Admin: Account Orchestration via MySQL."""
    _verify_super_admin(x_admin_secret)
    supabase = get_supabase()
    result = supabase.table("tenants").select(
        "id, name, email, plan, is_active, message_count, whatsapp_enabled, shopify_enabled, created_at"
    ).order("created_at", desc=True).execute()
    return {"tenants": result.data or [], "total": len(result.data or [])}


@router.post("/tenants")
async def create_tenant(body: CreateTenantRequest, x_admin_secret: str = Header(...)):
    """
    Create new tenant — "When a new business signs up, Super Admin triggers
    script to create new unique Tenant ID in MySQL"
    """
    _verify_super_admin(x_admin_secret)
    supabase = get_supabase()

    # Create tenant
    tenant = supabase.table("tenants").insert({
        "name": body.name,
        "email": body.email,
        "plan": body.plan
    }).execute()

    tenant_id = tenant.data[0]["id"]

    # Create default bot config
    supabase.table("bot_configs").insert({
        "tenant_id": tenant_id,
        "bot_name": f"{body.name} Assistant"
    }).execute()

    return {
        "success": True,
        "tenant_id": tenant_id,
        "message": f"Tenant {body.name} created with ID {tenant_id}"
    }


@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    body: UpdateTenantRequest,
    x_admin_secret: str = Header(...)
):
    """
    Toggle features per tenant.
    "Manages which features (WhatsApp/Shopify/AI models) are active for which client"
    """
    _verify_super_admin(x_admin_secret)
    supabase = get_supabase()

    update_data = {k: v for k, v in body.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_data["updated_at"] = "now()"
    result = supabase.table("tenants").update(update_data).eq("id", tenant_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {"success": True, "updated": update_data}


# ─────────────────────────────────────────────────────────────
# BILLING & USAGE (Super Admin auditing)
# ─────────────────────────────────────────────────────────────

@router.get("/tenants/{tenant_id}/usage")
async def get_tenant_usage(tenant_id: str, x_admin_secret: str = Header(...)):
    """
    "Super Admin queries MySQL to see how many messages each client
     has used for billing and performance auditing"
    """
    _verify_super_admin(x_admin_secret)
    supabase = get_supabase()

    tenant = supabase.table("tenants").select(
        "name, email, plan, message_count"
    ).eq("id", tenant_id).single().execute()

    docs = supabase.table("documents").select("id, file_name, file_size, status").eq(
        "tenant_id", tenant_id
    ).execute()

    chunks = supabase.table("document_chunks").select(
        "id", count="exact"
    ).eq("tenant_id", tenant_id).execute()

    return {
        "tenant": tenant.data,
        "documents": docs.data or [],
        "total_chunks": chunks.count or 0,
        "total_documents": len(docs.data or [])
    }


# ─────────────────────────────────────────────────────────────
# SYSTEM HEALTH (Redis monitoring)
# ─────────────────────────────────────────────────────────────

@router.get("/system/health")
async def system_health(x_admin_secret: str = Header(...)):
    """
    "Super Admin monitors Redis for system health.
     If Redis hits memory limit, dashboard alerts to scale Railway"
    """
    _verify_super_admin(x_admin_secret)
    redis = get_redis_service()
    supabase = get_supabase()

    active_sessions = await redis.get_active_sessions_count()

    tenant_count = supabase.table("tenants").select("id", count="exact").execute()
    msg_count = supabase.table("messages").select("id", count="exact").execute()

    return {
        "status": "healthy",
        "environment": "staging",
        "redis": {
            "active_sessions": active_sessions,
            "provider": "Upstash (free tier)"
        },
        "database": {
            "total_tenants": tenant_count.count or 0,
            "total_messages": msg_count.count or 0,
            "provider": "Supabase PostgreSQL (free tier)"
        },
        "llm": {
            "provider": "Groq",
            "model": get_settings().llm_model
        },
        "storage": {
            "provider": "Supabase Storage (free tier)"
        }
    }


# ─────────────────────────────────────────────────────────────
# PGVECTOR DEBUGGING (Super Admin)
# ─────────────────────────────────────────────────────────────

@router.get("/tenants/{tenant_id}/debug/vectors")
async def debug_tenant_vectors(
    tenant_id: str,
    document_id: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    x_admin_secret: str = Header(...)
):
    """
    "If client reports bot giving wrong answers, Super Admin can look at
     specific embeddings and search results in PGVector"
    """
    _verify_super_admin(x_admin_secret)
    retrieval = get_retrieval_service()

    if document_id:
        chunks = retrieval.debug_embeddings(tenant_id, document_id)
        return {"debug_type": "document_chunks", "document_id": document_id, "chunks": chunks}

    if query:
        chunks = await retrieval.retrieve(tenant_id, query, top_k=10)
        return {"debug_type": "query_results", "query": query, "results": chunks}

    return {"error": "Provide document_id or query parameter"}


@router.post("/tenants/{tenant_id}/reindex")
async def reindex_tenant(tenant_id: str, x_admin_secret: str = Header(...)):
    """
    "If we release update to Intention Engine, Super Admin orchestrates
     re-indexing of vectors across all client accounts"
    """
    _verify_super_admin(x_admin_secret)
    retrieval = get_retrieval_service()
    result = retrieval.reindex_tenant(tenant_id)
    return result


# ─────────────────────────────────────────────────────────────
# SUPPORT TICKETS (Supabase component)
# ─────────────────────────────────────────────────────────────

class CreateTicketRequest(BaseModel):
    tenant_id: str
    subject: str
    description: str
    priority: str = "medium"
    created_by_email: str


@router.get("/support/tickets")
async def list_tickets(
    status: Optional[str] = Query(None),
    x_admin_secret: str = Header(...)
):
    """List all support tickets — Super Admin support center via Supabase."""
    _verify_super_admin(x_admin_secret)
    supabase = get_supabase()
    query = supabase.table("support_tickets").select(
        "*, tenants(name, email)"
    ).order("created_at", desc=True)

    if status:
        query = query.eq("status", status)

    result = query.execute()
    return {"tickets": result.data or []}


@router.post("/support/tickets")
async def create_ticket(body: CreateTicketRequest):
    """Create support ticket — no auth needed (client-facing)."""
    supabase = get_supabase()
    result = supabase.table("support_tickets").insert(body.dict()).execute()
    return {"success": True, "ticket_id": result.data[0]["id"]}


@router.put("/support/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    status: str = Query(...),
    notes: Optional[str] = Query(None),
    x_admin_secret: str = Header(...)
):
    """Update ticket status — Super Admin resolves issues."""
    _verify_super_admin(x_admin_secret)
    supabase = get_supabase()

    update = {"status": status, "updated_at": "now()"}
    if notes:
        update["notes"] = notes

    supabase.table("support_tickets").update(update).eq("id", ticket_id).execute()
    return {"success": True, "ticket_id": ticket_id, "new_status": status}
