from supabase import create_client, Client
from .config import get_settings

def get_supabase() -> Client:
    """Initialize and return the Supabase client."""
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
