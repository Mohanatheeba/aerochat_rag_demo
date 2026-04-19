"""
LLM Service — Groq API (FREE Tier)
Equivalent to: Any paid LLM provider in production

Free tier: 14,400 req/day, 6000 tokens/min, llama3-70b-8192

Step 4 of Real-Time Flow (from architecture doc):
"Backend combines Fact from PGVector + Live Data from Shopify →
 sends to LLM to wrap in natural, human-sounding sentence"
"""

import time
from groq import Groq
from app.core.config import get_settings
from typing import Optional


class LLMService:
    """
    Generates responses using retrieved context + session history.
    """

    SYSTEM_PROMPT_TEMPLATE = """You are {bot_name}, a helpful customer service assistant.

Use the provided context to answer the customer's question accurately.
If the context doesn't contain the answer, say you don't have that information.
Be concise, friendly, and professional.

{custom_instructions}

KNOWLEDGE BASE CONTEXT:
{context}

{shopify_data}
"""

    def __init__(self):
        settings = get_settings()
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.llm_model

    def generate_response(
        self,
        user_query: str,
        context: str,
        session_history: list[dict],
        bot_name: str = "AeroChat Assistant",
        custom_instructions: str = "",
        shopify_data: str = "",
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> tuple[str, int]:
        """
        Generate LLM response combining RAG context + session memory.
        
        Returns: (response_text, latency_ms)
        """
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
            bot_name=bot_name,
            custom_instructions=custom_instructions or "Be helpful and concise.",
            context=context if context else "No specific knowledge base context available.",
            shopify_data=f"LIVE ORDER DATA:\n{shopify_data}" if shopify_data else ""
        )

        # Build messages: system + history + current query
        messages = [{"role": "system", "content": system_prompt}]

        # Add session context from Redis (last N messages)
        for msg in session_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add current user message
        messages.append({"role": "user", "content": user_query})

        start_time = time.time()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )

        latency_ms = int((time.time() - start_time) * 1000)
        response_text = response.choices[0].message.content

        return response_text, latency_ms

    def check_intent(self, query: str) -> dict:
        """
        Intent classification — categorize user's intent.
        Supports: Shopify queries, college NPC lookup
        """
        shopify_keywords = [
            "order", "track", "delivery", "shipping", "where is my",
            "return", "refund", "product", "inventory", "stock", "price"
        ]
        college_keywords = [
            "npc", "college", "university", "cutoff", "marks", "rank",
            "engineering", "medical", "admission", "counselling", "score",
            "tier 1", "tier 2", "tier 3", "iit", "nit", "iiit"
        ]
        
        query_lower = query.lower()
        is_shopify = any(kw in query_lower for kw in shopify_keywords)
        is_college = any(kw in query_lower for kw in college_keywords)

        return {
            "requires_shopify": is_shopify,
            "requires_college_lookup": is_college,
            "query_type": "order_tracking" if is_shopify else ("college_npc" if is_college else "general")
        }


_llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
