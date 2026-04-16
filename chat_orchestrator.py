"""
Chat Orchestrator — The Complete Real-Time Flow
Implements all 5 steps from the AeroChat architecture doc:

Step 1: Webhook trigger (customer message received)
Step 2: Semantic retrieval via PGVector cosine search
Step 3: Live data injection from Shopify (if order query)
Step 4: Response generation via LLM (Groq/llama3)
Step 5: Delivery + logging to MySQL (Supabase) + Redis update
"""

import uuid
import time
from app.core.supabase_client import get_supabase
from app.services.redis_session import get_redis_service
from app.services.retrieval_service import get_retrieval_service
from app.services.llm_service import get_llm_service
from app.services.shopify_service import get_shopify_service


class ChatOrchestrator:
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
        channel: str = "widget",   # 'widget' or 'whatsapp'
        customer_identifier: str = ""
    ) -> dict:
        """
        Main chat handler — orchestrates all 5 steps.
        
        Returns:
            {
                response: str,
                session_id: str,
                sources: list,
                latency_ms: int
            }
        """
        start_time = time.time()

        # ──────────────────────────────────────────────────────
        # STEP 1: Touchpoint Trigger
        # ──────────────────────────────────────────────────────
        # Get/create conversation in Supabase (MySQL equivalent)
        conversation_id = await self._get_or_create_conversation(
            tenant_id, session_id, channel, customer_identifier
        )

        # Get tenant config and bot settings
        bot_config = self._get_bot_config(tenant_id)
        tenant_info = self._get_tenant_info(tenant_id)

        # ──────────────────────────────────────────────────────
        # STEP 2: Semantic Retrieval (Vector Search)
        # ──────────────────────────────────────────────────────
        context, retrieved_chunks = await self.retrieval.get_context_string(
            tenant_id, user_message
        )

        # ──────────────────────────────────────────────────────
        # STEP 3: Live Data Injection (Shopify)
        # ──────────────────────────────────────────────────────
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
                    if order:
                        shopify_data = self.shopify.format_order_for_llm(order)
                elif "product" in user_message.lower() or "stock" in user_message.lower():
                    products = await self.shopify.get_product_info(
                        tenant_info["shopify_domain"],
                        tenant_info["shopify_access_token"],
                        user_message
                    )
                    if products:
                        shopify_data = "\n".join(
                            f"Product: {p['title']} | In Stock: {p['in_stock']} | Price: {p['price_range']}"
                            for p in products
                        )

        # ──────────────────────────────────────────────────────
        # Get Redis session context (conversation memory)
        # ──────────────────────────────────────────────────────
        session_history = await self.redis.get_context(session_id)

        # ──────────────────────────────────────────────────────
        # STEP 4: Response Generation (LLM)
        # ──────────────────────────────────────────────────────
        bot_name = bot_config.get("bot_name", "Assistant") if bot_config else "Assistant"
        system_prompt = bot_config.get("system_prompt", "") if bot_config else ""
        temperature = bot_config.get("temperature", 0.7) if bot_config else 0.7
        max_tokens = bot_config.get("max_tokens", 500) if bot_config else 500

        response_text, llm_latency = self.llm.generate_response(
            user_query=user_message,
            context=context,
            session_history=session_history,
            bot_name=bot_name,
            custom_instructions=system_prompt,
            shopify_data=shopify_data,
            temperature=temperature,
            max_tokens=max_tokens
        )

        total_latency = int((time.time() - start_time) * 1000)

        # ──────────────────────────────────────────────────────
        # STEP 5: Delivery + Logging
        # ──────────────────────────────────────────────────────

        # 5a. Save conversation to MySQL (Supabase PostgreSQL)
        await self._log_messages(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_message=user_message,
            assistant_response=response_text,
            sources=retrieved_chunks,
            latency_ms=total_latency
        )

        # 5b. Update Redis session context
        await self.redis.append_message(session_id, "user", user_message)
        await self.redis.append_message(session_id, "assistant", response_text)

        # 5c. Increment message count for tenant (billing tracking)
        self._increment_message_count(tenant_id)

        return {
            "response": response_text,
            "session_id": session_id,
            "conversation_id": conversation_id,
            "sources": [
                {
                    "chunk_preview": c["chunk_text"][:100] + "...",
                    "similarity": round(c["similarity"], 3)
                }
                for c in retrieved_chunks[:2]  # Show top 2 sources
            ],
            "latency_ms": total_latency
        }

    async def _get_or_create_conversation(
        self, tenant_id: str, session_id: str, channel: str, customer_identifier: str
    ) -> str:
        """Get existing or create new conversation record."""
        existing = self.supabase.table("conversations").select("id").eq(
            "session_id", session_id
        ).eq("tenant_id", tenant_id).execute()

        if existing.data:
            conv_id = existing.data[0]["id"]
            # Update last message time
            self.supabase.table("conversations").update({
                "last_message_at": "now()",
                "message_count": self.supabase.raw("message_count + 1")
            }).eq("id", conv_id).execute()
            return conv_id

        # Create new conversation
        result = self.supabase.table("conversations").insert({
            "tenant_id": tenant_id,
            "session_id": session_id,
            "channel": channel,
            "customer_identifier": customer_identifier,
            "message_count": 1
        }).execute()

        return result.data[0]["id"]

    async def _log_messages(
        self,
        conversation_id: str,
        tenant_id: str,
        user_message: str,
        assistant_response: str,
        sources: list,
        latency_ms: int
    ):
        """Log both messages to Supabase (MySQL equivalent)."""
        self.supabase.table("messages").insert([
            {
                "conversation_id": conversation_id,
                "tenant_id": tenant_id,
                "role": "user",
                "content": user_message,
                "sources": [],
                "latency_ms": 0
            },
            {
                "conversation_id": conversation_id,
                "tenant_id": tenant_id,
                "role": "assistant",
                "content": assistant_response,
                "sources": [
                    {"chunk_preview": s["chunk_text"][:150], "similarity": s["similarity"]}
                    for s in sources
                ],
                "latency_ms": latency_ms
            }
        ]).execute()

    def _get_bot_config(self, tenant_id: str) -> dict | None:
        """Fetch bot configuration for tenant."""
        result = self.supabase.table("bot_configs").select("*").eq(
            "tenant_id", tenant_id
        ).execute()
        return result.data[0] if result.data else None

    def _get_tenant_info(self, tenant_id: str) -> dict | None:
        """Fetch tenant info (Shopify credentials etc)."""
        result = self.supabase.table("tenants").select(
            "shopify_enabled, shopify_domain, shopify_access_token"
        ).eq("id", tenant_id).execute()
        return result.data[0] if result.data else None

    def _increment_message_count(self, tenant_id: str):
        """Track message usage for Super Admin billing."""
        try:
            self.supabase.table("tenants").update({
                "message_count": self.supabase.raw("message_count + 1")
            }).eq("id", tenant_id).execute()
        except Exception:
            pass


_chat_orchestrator = None

def get_chat_orchestrator() -> ChatOrchestrator:
    global _chat_orchestrator
    if _chat_orchestrator is None:
        _chat_orchestrator = ChatOrchestrator()
    return _chat_orchestrator
