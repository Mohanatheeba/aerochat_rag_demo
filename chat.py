"""
Chat API Routes
- POST /chat/message      → Main chat handler (widget/WhatsApp)
- POST /chat/webhook/whatsapp → WhatsApp webhook handler
- GET  /chat/webhook/whatsapp → WhatsApp webhook verification
- GET  /chat/history/{session_id} → Get session history
"""

import uuid
import hashlib
import hmac
import json
from fastapi import APIRouter, HTTPException, Request, Query, Header
from pydantic import BaseModel
from typing import Optional

from app.services.chat_orchestrator import get_chat_orchestrator
from app.services.redis_session import get_redis_service
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/chat", tags=["chat"])


# ─────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    tenant_id: str
    message: str
    session_id: Optional[str] = None
    channel: str = "widget"
    customer_identifier: Optional[str] = ""


class ChatResponse(BaseModel):
    response: str
    session_id: str
    conversation_id: str
    sources: list
    latency_ms: int


# ─────────────────────────────────────────────────────────────
# MAIN CHAT ENDPOINT (Widget + API)
# ─────────────────────────────────────────────────────────────

@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """
    Main chat endpoint — Step 1 of real-time flow (Touchpoint Trigger).
    Handles messages from web widget or direct API calls.
    """
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    orchestrator = get_chat_orchestrator()
    result = await orchestrator.process_message(
        tenant_id=request.tenant_id,
        user_message=request.message,
        session_id=session_id,
        channel=request.channel,
        customer_identifier=request.customer_identifier or ""
    )

    return ChatResponse(**result)


# ─────────────────────────────────────────────────────────────
# WHATSAPP WEBHOOK (Meta Cloud API)
# ─────────────────────────────────────────────────────────────

@router.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify.token"),
    tenant_id: str = Query(...)
):
    """
    WhatsApp webhook verification (Meta requires GET verification).
    """
    supabase = get_supabase()
    tenant = supabase.table("tenants").select(
        "whatsapp_verify_token"
    ).eq("id", tenant_id).execute()

    if not tenant.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    verify_token = tenant.data[0].get("whatsapp_verify_token", "")

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return int(hub_challenge)

    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, tenant_id: str = Query(...)):
    """
    WhatsApp incoming message handler.
    Receives messages from Meta and processes through RAG pipeline.
    """
    body = await request.body()
    data = json.loads(body)

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return {"status": "no_message"}

        message = value["messages"][0]
        from_number = message["from"]
        message_text = message.get("text", {}).get("body", "")

        if not message_text:
            return {"status": "non_text_message"}

        # Use phone number as session ID for WhatsApp
        session_id = f"wa_{from_number}"

        orchestrator = get_chat_orchestrator()
        result = await orchestrator.process_message(
            tenant_id=tenant_id,
            user_message=message_text,
            session_id=session_id,
            channel="whatsapp",
            customer_identifier=from_number
        )

        # Send reply back via WhatsApp Cloud API
        await _send_whatsapp_reply(
            tenant_id=tenant_id,
            to_number=from_number,
            message=result["response"]
        )

        return {"status": "ok"}

    except (KeyError, IndexError):
        return {"status": "invalid_payload"}


async def _send_whatsapp_reply(tenant_id: str, to_number: str, message: str):
    """Send reply via WhatsApp Cloud API (free tier)."""
    import httpx
    supabase = get_supabase()
    tenant = supabase.table("tenants").select(
        "whatsapp_phone_number_id"
    ).eq("id", tenant_id).execute()

    if not tenant.data:
        return

    phone_number_id = tenant.data[0].get("whatsapp_phone_number_id")
    # Note: WA_ACCESS_TOKEN would be stored per-tenant in production
    # For staging, use environment variable
    import os
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")

    if not phone_number_id or not access_token:
        return

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://graph.facebook.com/v19.0/{phone_number_id}/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": message}
            },
            timeout=10.0
        )


# ─────────────────────────────────────────────────────────────
# SESSION / HISTORY
# ─────────────────────────────────────────────────────────────

@router.get("/history/{session_id}")
async def get_session_history(session_id: str, tenant_id: str = Query(...)):
    """Get conversation messages from Supabase (MySQL equivalent)."""
    supabase = get_supabase()
    conv = supabase.table("conversations").select("id").eq(
        "session_id", session_id
    ).eq("tenant_id", tenant_id).execute()

    if not conv.data:
        return {"messages": [], "session_id": session_id}

    messages = supabase.table("messages").select(
        "role, content, created_at, latency_ms"
    ).eq("conversation_id", conv.data[0]["id"]).order("created_at").execute()

    return {
        "session_id": session_id,
        "messages": messages.data or []
    }


@router.delete("/session/{session_id}")
async def clear_session(session_id: str, tenant_id: str = Query(...)):
    """Clear Redis session context."""
    redis = get_redis_service()
    await redis.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}
