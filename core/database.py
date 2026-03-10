<<<<<<< HEAD
"""
Database Configuration Module.

Initializes the Supabase client for database interactions.
"""

from supabase import create_client, Client
from core.config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
=======
from supabase import create_client, Client
from core.config import SUPABASE_URL, SUPABASE_KEY

>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
