"""
Database connection management for Supabase/PostgreSQL.
"""

from typing import Optional
from supabase import create_client, Client
import asyncpg

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

# Global connection instances
_supabase_client: Optional[Client] = None
_pg_pool: Optional[asyncpg.Pool] = None


async def init_db() -> bool:
    """Initialize database connections. Returns True if successful."""
    global _supabase_client, _pg_pool
    
    # Initialize Supabase client
    if settings.supabase_url and settings.supabase_service_role_key:
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        logger.info("Supabase client initialized")
    else:
        logger.warning("Supabase credentials not configured")
    
    # Initialize direct PostgreSQL connection for advanced queries
    if settings.database_url:
        try:
            _pg_pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=5,
                max_size=20
            )
            logger.info("PostgreSQL connection pool initialized")
            return True
        except Exception as e:
            logger.warning(f"Could not connect to PostgreSQL: {e}")
            return False
    
    return _supabase_client is not None


async def close_db() -> None:
    """Close database connections."""
    global _pg_pool
    
    if _pg_pool:
        await _pg_pool.close()
        logger.info("PostgreSQL connection pool closed")


def get_supabase() -> Optional[Client]:
    """Get the Supabase client instance."""
    return _supabase_client


async def get_pg_pool() -> Optional[asyncpg.Pool]:
    """Get the PostgreSQL connection pool."""
    return _pg_pool


async def execute_query(query: str, *args) -> list:
    """Execute a SQL query and return results."""
    if not _pg_pool:
        raise RuntimeError("Database not initialized")
    
    async with _pg_pool.acquire() as conn:
        result = await conn.fetch(query, *args)
        return [dict(row) for row in result]


async def execute_one(query: str, *args) -> Optional[dict]:
    """Execute a SQL query and return a single result."""
    if not _pg_pool:
        raise RuntimeError("Database not initialized")
    
    async with _pg_pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None
