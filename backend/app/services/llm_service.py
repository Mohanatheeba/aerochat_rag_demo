import time
from groq import Groq
from ..core.config import get_settings
from typing import Optional, List, Dict, Tuple

class LLMService:
    """
    Generates responses using retrieved context + session history via Groq (Free Tier).
    """

    SYSTEM_PROMPT_TEMPLATE = """You are {bot_name}, a highly intelligent customer service assistant.
Your goal is to answer questions accurately based on the provided context.

HANDLING TIER 3 COLLEGES:
- If the user asks about a college NOT in Tier 1/2, the system may provide Tier 3 college lookup results.
- Tier 3 results are prefixed with "TIER 3 COLLEGE CALCULATION RESULT:" or "TIER 3 COLLEGE DATA:".
- Present Tier 3 results clearly with the college name, NPC score, and eligibility status.
- If Tier 3 lookup fails, provide helpful guidance on how the user can calculate NPC themselves.

SEMANTIC GUIDELINES:
- "Personal Information" includes: Email addresses, Phone numbers, LinkedIn profiles, Portfolios, GitHub, and Home addresses.
- "Designation" includes: Current job titles, latest educational degrees, and professional roles.
- If a user asks generic questions like "tell me about her", look for names, skills, and experience sections.

RETRIEVAL GUIDELINES:
1. Use the "KNOWLEDGE BASE CONTEXT" to answer. It contains document chunks retrieved for this specific query.
2. If the answer isn't explicitly stated but can be clearly deduced (e.g. the name at the top of a resume is the holder), provide the deduction.
3. If the context absolutely does not contain the answer, politely say you don't have that information.
4. For college queries without Tier 1/2 context: use TIER 3 COLLEGE DATA if available, or guide the user to find the information.
5. Keep your tone professional, concise, and helpful.

{custom_instructions}

KNOWLEDGE BASE CONTEXT:
{context}

{shopify_data}
"""

    def __init__(self):
        self.settings = get_settings()
        self.client = Groq(api_key=self.settings.GROQ_API_KEY)
        self.model = self.settings.LLM_MODEL

    def generate_response(
        self,
        user_query: str,
        context: str,
        session_history: List[Dict],
        bot_name: str = "AeroChat Assistant",
        custom_instructions: str = "",
        shopify_data: str = "",
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Tuple[str, int]:
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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            response_text = response.choices[0].message.content
        except Exception as e:
            response_text = f"Error generating response: {str(e)}"

        latency_ms = int((time.time() - start_time) * 1000)

        return response_text, latency_ms

    def refine_query(self, user_query: str) -> str:
        """
        Hyper-Advanced Intent Analysis: 
        1. Analyzes user's underlying goal.
        2. Resolves pronouns (her, him, this person).
        3. Expands synonyms for broad semantic matching.
        """
        refinement_prompt = f"""Target: AI-Driven Vector Search Optimization.
Task: Understand the user's INTENT and expand the query for a high-accuracy document search.

Context: The documents in the database are likely resumes or business profiles.

Instructions:
1. Determine what the user is SPECIFICALLY looking for (e.g., Contact info, Skills, Role, History).
2. Resolve pronouns (her/him/they) to mean 'the person described in the document'.
3. Map general terms to specific keywords:
   - 'Personal Information' -> 'email, phone, contact, linkedin, address'
   - 'Designation/Status' -> 'current job title, role, educational degree, graduation status'
   - 'Experience' -> 'past jobs, work history, responsibilities, projects'
4. Output ONLY the optimized, highly descriptive search string.

User Query: "{user_query}"
Optimized Search String:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": refinement_prompt}],
                temperature=0.1,
                max_tokens=100
            )
            refined = response.choices[0].message.content.strip().strip('"')
            # Log for debugging (visible in user's terminal)
            print(f"🤖 Intent Mapping: '{user_query}' → '{refined}'")
            return refined
        except:
            return user_query

    def check_intent(self, query: str) -> Dict:
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
