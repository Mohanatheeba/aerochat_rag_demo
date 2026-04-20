import time
import uuid
from typing import Optional, Dict, List
from ..core.supabase_client import get_supabase
from ..services.redis_service import get_redis_service
from ..services.retrieval_service import get_retrieval_service
from ..services.llm_service import get_llm_service
from ..services.shopify_service import get_shopify_service

class ChatOrchestrator:
    """
    Orchestrates the 5-step RAG flow:
    Trigger -> Retrieve -> Live Data -> Generate -> Log
    """

    def __init__(self):
        self.supabase = get_supabase()
        self.redis = get_redis_service()
        self.retrieval = get_retrieval_service()
        self.llm = get_llm_service()
        self.shopify = get_shopify_service()

    async def process_message(
        self,
        tenant_id: str,
        user_message: str,
        session_id: str,
        channel: str = "widget",
        customer_identifier: str = ""
    ) -> Dict:
        try:
            start_time = time.time()

            # Step 1: Context & Intent
            bot_config = await self._get_bot_config(tenant_id)
            tenant_info = await self._get_tenant_info(tenant_id)
            
            # Step 2: Semantic Retrieval
            print(f"🔍 [RAG] Retrieving for: {user_message[:50]}")
            context, retrieved_chunks = await self.retrieval.get_context_string(tenant_id, user_message)
            print(f"   [RAG] Found {len(retrieved_chunks)} chunks.")

            # Step 3: Live Data (Shopify)
            shopify_data = ""
            if tenant_info and tenant_info.get("shopify_enabled"):
                intent = self.llm.check_intent(user_message)
                if intent["requires_shopify"]:
                    order_number = self.shopify.extract_order_number(user_message)
                    if order_number:
                        order = await self.shopify.get_order_by_number(
                            tenant_info["shopify_domain"],
                            tenant_info["shopify_access_token"],
                            order_number
                        )
                        shopify_data = self.shopify.format_order_for_llm(order)

            # Step 4: Generation
            print("🧠 [LLM] Generating response...")
            session_history = await self.redis.get_context(session_id)
            response_text, llm_latency = self.llm.generate_response(
                user_query=user_message,
                context=context,
                session_history=session_history,
                bot_name=bot_config.get("bot_name", "Assistant"),
                custom_instructions=bot_config.get("system_prompt", ""),
                shopify_data=shopify_data
            )

            total_latency = int((time.time() - start_time) * 1000)

            # Step 5: Logging & Update
            await self.redis.append_message(session_id, "user", user_message)
            await self.redis.append_message(session_id, "assistant", response_text)
            
            # Async logging (simplified for staging)
            self._log_interaction(tenant_id, session_id, user_message, response_text, total_latency)

            return {
                "response": response_text,
                "session_id": session_id,
                "latency_ms": total_latency,
                "sources": [{"text": c["chunk_text"][:100], "score": c["similarity"]} for c in retrieved_chunks[:2]]
            }
        except Exception as e:
            import traceback
            print(f"❌ [ORCHESTRATOR ERROR]: {str(e)}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    async def _get_bot_config(self, tenant_id: str) -> Dict:
        res = self.supabase.table("bot_configs").select("*").eq("tenant_id", tenant_id).execute()
        return res.data[0] if res.data else {}

    async def _get_tenant_info(self, tenant_id: str) -> Dict:
        res = self.supabase.table("tenants").select("*").eq("id", tenant_id).execute()
        return res.data[0] if res.data else {}

    def _log_interaction(self, tenant_id, session_id, user_message, response_text, latency):
        try:
            self.supabase.table("messages").insert([
                {"tenant_id": tenant_id, "role": "user", "content": user_message},
                {"tenant_id": tenant_id, "role": "assistant", "content": response_text, "latency_ms": latency}
            ]).execute()
        except Exception as e:
            print(f"Log Error: {e}")

_chat_orchestrator: Optional[ChatOrchestrator] = None

def get_chat_orchestrator() -> ChatOrchestrator:
    global _chat_orchestrator
    if _chat_orchestrator is None:
        _chat_orchestrator = ChatOrchestrator()
    return _chat_orchestrator
