import json
from typing import List, Dict, Optional
import httpx
from ..core.config import get_settings

class RedisService:
    """
    Session management using Upstash Redis (HTTP REST API).
    100% Free Tier compatible.
    """
    
    def __init__(self):
        settings = get_settings()
        self.url = settings.UPSTASH_REDIS_REST_URL
        self.token = settings.UPSTASH_REDIS_REST_TOKEN
        self.headers = {"Authorization": f"Bearer {self.token}"}

    async def _run_command(self, command: List[str]) -> any:
        """Execute a Redis command via Upstash REST API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=command, headers=self.headers)
                return response.json().get("result")
            except Exception as e:
                print(f"Redis Error: {e}")
                return None

    async def get_context(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Fetch message history from Redis list."""
        key = f"chat_history:{session_id}"
        items = await self._run_command(["LRANGE", key, "-10", "-1"])
        
        if not items:
            return []
            
        return [json.loads(item) for item in items]

    async def append_message(self, session_id: str, role: str, content: str):
        """Add a message to the session context."""
        key = f"chat_history:{session_id}"
        message = json.dumps({"role": role, "content": content})
        
        # PUSH to list
        await self._run_command(["RPUSH", key, message])
        
        # Set expiry (24 hours)
        await self._run_command(["EXPIRE", key, "86400"])

    async def clear_session(self, session_id: str):
        """Delete session history."""
        key = f"chat_history:{session_id}"
        await self._run_command(["DEL", key])

_redis_service: Optional[RedisService] = None

def get_redis_service() -> RedisService:
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
    return _redis_service
