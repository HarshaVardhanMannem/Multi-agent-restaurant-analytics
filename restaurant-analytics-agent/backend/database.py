"""
Supabase Database Connection Pool
Handles async PostgreSQL connections with SSL support
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import asyncpg

from .config.settings import get_settings

logger = logging.getLogger(__name__)


class SupabasePool:
    """
    Async connection pool for Supabase PostgreSQL database.
    Uses asyncpg with SSL for secure connections.
    """

    pool: asyncpg.Pool | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    async def connect(cls) -> None:
        """Initialize the connection pool"""
        async with cls._lock:
            if cls.pool is not None:
                logger.info("Pool already initialized")
                return

            settings = get_settings()

            logger.info("Connecting to Supabase PostgreSQL...")

            # Get database URL (supports multiple config formats)
            try:
                db_url = settings.get_database_url()
                # Log connection info (mask password for security)
                masked_url = db_url.split('@')[1] if '@' in db_url else '***'
                logger.info(f"Connecting to database: postgresql://***@{masked_url}")
            except ValueError as e:
                logger.error(f"Database configuration error: {e}")
                logger.error("Please set SUPABASE_DB_URL or SUPABASE_URL + SUPABASE_PASSWORD environment variables")
                raise

            cls.pool = await asyncpg.create_pool(
                dsn=db_url,
                ssl="require",  # Supabase requires SSL
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size,
                command_timeout=settings.db_command_timeout,
                # Connection health checks
                setup=cls._setup_connection,
            )

            logger.info(
                f"Connection pool created: "
                f"min={settings.db_pool_min_size}, max={settings.db_pool_max_size}"
            )

            # Test the connection
            await cls._test_connection()

    @classmethod
    async def _setup_connection(cls, connection: asyncpg.Connection) -> None:
        """Setup function called for each new connection"""
        # Set session parameters
        await connection.execute("SET timezone = 'UTC'")

    @classmethod
    async def _test_connection(cls) -> None:
        """Test the database connection"""
        async with cls.pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            if result != 1:
                raise RuntimeError("Connection test failed")
            logger.info("Database connection test successful")

    @classmethod
    async def disconnect(cls) -> None:
        """Close the connection pool"""
        async with cls._lock:
            if cls.pool is not None:
                await cls.pool.close()
                cls.pool = None
                logger.info("Connection pool closed")

    @classmethod
    async def _ensure_connected(cls) -> None:
        """Ensure database connection is established, retry if needed"""
        if cls.pool is None:
            logger.info("Database pool not initialized, attempting to connect...")
            try:
                await cls.connect()
            except Exception as e:
                logger.error(f"Failed to establish database connection: {e}")
                raise RuntimeError(f"Database connection not available: {e}")

    @classmethod
    async def execute_query(
        cls,
        sql: str,
        *args,
        timeout: int | None = None,
    ) -> tuple[list[dict[str, Any]], float]:
        """
        Execute a SELECT query and return results as list of dicts.

        Args:
            sql: The SQL query to execute (can use $1, $2, etc. for parameters)
            *args: Query parameters (positional arguments after sql)
            timeout: Query timeout in seconds (optional)

        Returns:
            Tuple of (results list, execution time in ms)
        """
        # Ensure connection is established (lazy connection)
        if cls.pool is None:
            await cls._ensure_connected()

        settings = get_settings()
        timeout = timeout or settings.max_query_timeout

        start_time = time.perf_counter()

        async with cls.pool.acquire() as conn:
            try:
                # Set statement timeout for this query (in milliseconds)
                timeout_ms = timeout * 1000
                await conn.execute(f"SET statement_timeout = {timeout_ms}")

                # Execute the query with parameters if provided
                if args:
                    rows = await conn.fetch(sql, *args)
                else:
                    rows = await conn.fetch(sql)

                # Calculate execution time
                execution_time_ms = (time.perf_counter() - start_time) * 1000

                # Convert to list of dicts
                results = [dict(row) for row in rows]

                logger.info(f"Query executed: {len(results)} rows in {execution_time_ms:.2f}ms")

                return results, execution_time_ms

            except asyncpg.QueryCanceledError:
                logger.error(f"Query timeout after {timeout}s")
                raise TimeoutError(f"Query exceeded {timeout} second timeout")
            except asyncpg.PostgresError as e:
                logger.error(f"PostgreSQL error: {e}")
                raise
            finally:
                # Reset statement timeout to default
                await conn.execute("SET statement_timeout = 0")

    @classmethod
    async def execute_query_safe(
        cls,
        sql: str,
        timeout: int | None = None,
    ) -> tuple[list[dict[str, Any]] | None, float, str | None]:
        """
        Execute a query with error handling.

        Returns:
            Tuple of (results or None, execution time in ms, error message or None)
        """
        try:
            results, exec_time = await cls.execute_query(sql, timeout)
            return results, exec_time, None
        except TimeoutError as e:
            return None, 0.0, str(e)
        except asyncpg.PostgresError as e:
            return None, 0.0, f"Database error: {str(e)}"
        except Exception as e:
            return None, 0.0, f"Unexpected error: {str(e)}"

    @classmethod
    async def check_health(cls) -> bool:
        """Check if the database connection is healthy"""
        if cls.pool is None:
            return False

        try:
            async with cls.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    @classmethod
    @asynccontextmanager
    async def get_connection(cls) -> asyncpg.Connection:
        """Get a connection from the pool as a context manager"""
        if cls.pool is None:
            raise RuntimeError("Database pool not initialized")

        async with cls.pool.acquire() as conn:
            yield conn

    @classmethod
    async def get_pool_stats(cls) -> dict[str, Any]:
        """Get pool statistics"""
        if cls.pool is None:
            return {"status": "not_initialized"}

        return {
            "status": "connected",
            "size": cls.pool.get_size(),
            "free_size": cls.pool.get_idle_size(),
            "min_size": cls.pool.get_min_size(),
            "max_size": cls.pool.get_max_size(),
        }


# Convenience functions
async def init_database() -> None:
    """Initialize the database connection pool"""
    await SupabasePool.connect()


async def close_database() -> None:
    """Close the database connection pool"""
    await SupabasePool.disconnect()


async def execute_sql(sql: str, timeout: int = 30) -> list[dict[str, Any]]:
    """Execute SQL and return results"""
    results, _ = await SupabasePool.execute_query(sql, timeout)
    return results
