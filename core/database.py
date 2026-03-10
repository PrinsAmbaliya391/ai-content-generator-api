"""
Database Configuration Module.

Initializes the Supabase client for database interactions.
"""

from supabase import create_client, Client
from core.config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
