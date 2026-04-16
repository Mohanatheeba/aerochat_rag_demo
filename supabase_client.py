from supabase import create_client, Client
from app.core.config import get_settings
from functools import lru_cache

_supabase_client: Client | None = None


def get_supabase() -> Client:
    """
    Returns a singleton Supabase client using the SERVICE ROLE key.
    This bypasses RLS — equivalent to direct MySQL/S3/PGVector access.
    Used server-side only (never expose service key to frontend).
    """
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key  # Service role = full access
        )
    return _supabase_client
