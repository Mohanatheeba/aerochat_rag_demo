"""
Tenant & Bot Configuration API
- GET  /tenants/{id}/config  → Get bot config
- PUT  /tenants/{id}/config  → Update bot config
- GET  /tenants/{id}/stats   → Dashboard stats
- GET  /tenants/{id}/conversations → Conversation history
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/tenants", tags=["tenants"])


class BotConfigUpdate(BaseModel):
    bot_name: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    language: Optional[str] = None


@router.get("/{tenant_id}/config")
async def get_bot_config(tenant_id: str):
    """Get bot configuration for tenant dashboard."""
    supabase = get_supabase()
    result = supabase.table("bot_configs").select("*").eq("tenant_id", tenant_id).execute()

    if not result.data:
        # Create default config
        new_config = supabase.table("bot_configs").insert({
            "tenant_id": tenant_id
        }).execute()
        return new_config.data[0]

    return result.data[0]


@router.put("/{tenant_id}/config")
async def update_bot_config(tenant_id: str, body: BotConfigUpdate):
    """Update bot configuration."""
    supabase = get_supabase()
    update_data = {k: v for k, v in body.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_data["updated_at"] = "now()"

    result = supabase.table("bot_configs").update(update_data).eq(
        "tenant_id", tenant_id
    ).execute()

    return {"success": True, "config": result.data[0] if result.data else {}}


@router.get("/{tenant_id}/stats")
async def get_tenant_stats(tenant_id: str):
    """Dashboard stats for tenant."""
    supabase = get_supabase()

    tenant = supabase.table("tenants").select(
        "name, email, plan, message_count, is_active"
    ).eq("id", tenant_id).single().execute()

    docs = supabase.table("documents").select(
        "id, status", count="exact"
    ).eq("tenant_id", tenant_id).execute()

    conversations = supabase.table("conversations").select(
        "id", count="exact"
    ).eq("tenant_id", tenant_id).execute()

    indexed_docs = [d for d in (docs.data or []) if d["status"] == "indexed"]

    return {
        "tenant": tenant.data,
        "stats": {
            "total_messages": tenant.data.get("message_count", 0) if tenant.data else 0,
            "total_conversations": conversations.count or 0,
            "total_documents": docs.count or 0,
            "indexed_documents": len(indexed_docs)
        }
    }


@router.get("/{tenant_id}/conversations")
async def get_conversations(
    tenant_id: str,
    limit: int = Query(20, le=100),
    offset: int = Query(0)
):
    """Get conversation list for dashboard history view."""
    supabase = get_supabase()
    result = supabase.table("conversations").select(
        "id, session_id, channel, customer_identifier, message_count, started_at, last_message_at"
    ).eq("tenant_id", tenant_id).order(
        "last_message_at", desc=True
    ).range(offset, offset + limit - 1).execute()

    return {"conversations": result.data or []}


@router.get("/{tenant_id}/conversations/{conversation_id}/messages")
async def get_conversation_messages(tenant_id: str, conversation_id: str):
    """Get all messages for a specific conversation."""
    supabase = get_supabase()
    result = supabase.table("messages").select(
        "role, content, sources, latency_ms, created_at"
    ).eq("conversation_id", conversation_id).eq(
        "tenant_id", tenant_id
    ).order("created_at").execute()

    return {"messages": result.data or []}
