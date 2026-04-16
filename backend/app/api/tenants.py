from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..core.supabase_client import get_supabase

router = APIRouter(prefix="/tenants", tags=["Tenants"])

class BotConfigUpdate(BaseModel):
    bot_name: str
    system_prompt: str
    temperature: float = 0.7

@router.get("/{tenant_id}/config")
async def get_config(tenant_id: str):
    supabase = get_supabase()
    res = supabase.table("bot_configs").select("*").eq("tenant_id", tenant_id).execute()
    if not res.data:
        # Create default config if missing
        res = supabase.table("bot_configs").insert({"tenant_id": tenant_id}).execute()
    return res.data[0]

@router.put("/{tenant_id}/config")
async def update_config(tenant_id: str, config: BotConfigUpdate):
    supabase = get_supabase()
    res = supabase.table("bot_configs").update({
        "bot_name": config.bot_name,
        "system_prompt": config.system_prompt,
        "temperature": config.temperature,
        "updated_at": "now()"
    }).eq("tenant_id", tenant_id).execute()
    return res.data[0]
