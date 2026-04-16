"""
Redis Session Service — Upstash REST API (Free Tier)
Equivalent to: Redis (Railway) in AeroChat architecture
Role: Stores active chat session context so LLM remembers conversation

Upstash Free: 10,000 commands/day, no server needed — pure REST API
"""

import json
import httpx
from typing import Optional
from app.core.config import get_settings


class RedisSessionService:
    """
    Manages conversation context in Upstash Redis.
    
    Each session key: session:{session_id}
    Value: JSON list of last N messages (role + content)
    TTL: 1 hour by default (configurable)
    """

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.upstash_redis_rest_url.rstrip("/")
        self.token = settings.upstash_redis_rest_token
        self.ttl = settings.session_ttl_seconds
        self.max_messages = settings.max_context_messages
        self.headers = {"Authorization": f"Bearer {self.token}"}

    async def _command(self, *args) -> dict:
        """Execute a Redis command via Upstash REST API."""
        url = f"{self.base_url}/{'/'.join(str(a) for a in args)}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def _post_command(self, payload: list) -> dict:
        """Execute Redis command via POST (for complex commands)."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.base_url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
                timeout=10.0
            )
            resp.raise_for_status()
            return resp.json()

    def _session_key(self, session_id: str) -> str:
        return f"session:{session_id}"

    async def get_context(self, session_id: str) -> list[dict]:
        """
        Retrieve conversation context from Redis.
        Returns list of {role, content} messages.
        """
        key = self._session_key(session_id)
        try:
            result = await self._command("GET", key)
            if result.get("result"):
                return json.loads(result["result"])
        except Exception:
            pass
        return []

    async def append_message(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to session context and trim to max_messages.
        Also refreshes TTL on each interaction.
        """
        key = self._session_key(session_id)
        context = await self.get_context(session_id)

        context.append({"role": role, "content": content})

        # Keep only last N messages (sliding window)
        if len(context) > self.max_messages:
            context = context[-self.max_messages:]

        # Store back with TTL refresh
        await self._post_command(["SET", key, json.dumps(context), "EX", str(self.ttl)])

    async def clear_session(self, session_id: str) -> None:
        """Clear a session (e.g., on conversation end)."""
        key = self._session_key(session_id)
        await self._command("DEL", key)

    async def get_active_sessions_count(self) -> int:
        """
        Super Admin: Count active sessions across platform.
        Uses SCAN for key counting (approximate).
        """
        try:
            result = await self._command("DBSIZE")
            return result.get("result", 0)
        except Exception:
            return 0

    async def get_session_info(self, session_id: str) -> dict:
        """Get session metadata for Super Admin monitoring."""
        key = self._session_key(session_id)
        context = await self.get_context(session_id)
        ttl_result = await self._command("TTL", key)
        return {
            "session_id": session_id,
            "message_count": len(context),
            "ttl_seconds": ttl_result.get("result", -1),
            "context": context
        }


# Singleton
_redis_service: Optional[RedisSessionService] = None

def get_redis_service() -> RedisSessionService:
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisSessionService()
    return _redis_service
