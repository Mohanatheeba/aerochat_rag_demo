from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from ..services.chat_orchestrator import get_chat_orchestrator

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    tenant_id: str
    message: str
    session_id: str
    channel: str = "widget"
    customer_identifier: str = ""

@router.post("/message")
async def send_message(req: ChatRequest):
    orchestrator = get_chat_orchestrator()
    try:
        response = await orchestrator.process_message(
            tenant_id=req.tenant_id,
            user_message=req.message,
            session_id=req.session_id,
            channel=req.channel,
            customer_identifier=req.customer_identifier
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
