"""
Visualization Cache
In-memory cache for storing visualization state by query_id.
Visualizations are generated asynchronously and can be fetched on demand.
"""

import asyncio
import logging
import time
from typing import Optional
from collections import defaultdict

from ..models.state import VisualizationType, VisualizationConfig

logger = logging.getLogger(__name__)

# In-memory cache: query_id -> visualization data
_viz_cache: dict[str, dict] = {}
_cache_lock = asyncio.Lock()
_cache_metadata: dict[str, dict] = defaultdict(dict)  # Track creation time, etc.

# Cache expiration: 1 hour
CACHE_TTL_SECONDS = 3600


class VisualizationCache:
    """Thread-safe cache for visualization data"""

    @staticmethod
    async def store(
        query_id: str,
        viz_type: VisualizationType,
        viz_config: VisualizationConfig,
        chart_js_config: dict,
    ) -> None:
        """Store visualization data for a query_id"""
        async with _cache_lock:
            _viz_cache[query_id] = {
                "type": viz_type.value if hasattr(viz_type, "value") else str(viz_type),
                "config": dict(viz_config) if viz_config else {},
                "chart_js_config": chart_js_config,
            }
            _cache_metadata[query_id] = {
                "created_at": time.time(),
                "status": "ready",
            }
            logger.info(f"Stored visualization for query_id: {query_id}")

    @staticmethod
    async def get(query_id: str) -> Optional[dict]:
        """Get visualization data for a query_id"""
        async with _cache_lock:
            # Check if expired
            if query_id in _cache_metadata:
                created_at = _cache_metadata[query_id].get("created_at", 0)
                if time.time() - created_at > CACHE_TTL_SECONDS:
                    logger.info(f"Visualization cache expired for query_id: {query_id}")
                    del _viz_cache[query_id]
                    del _cache_metadata[query_id]
                    return None

            return _viz_cache.get(query_id)

    @staticmethod
    async def set_status(query_id: str, status: str) -> None:
        """Set the status of visualization generation (pending, ready, error)"""
        async with _cache_lock:
            if query_id in _cache_metadata:
                _cache_metadata[query_id]["status"] = status
            else:
                _cache_metadata[query_id] = {"status": status, "created_at": time.time()}

    @staticmethod
    async def get_status(query_id: str) -> str:
        """Get the status of visualization generation"""
        async with _cache_lock:
            return _cache_metadata.get(query_id, {}).get("status", "pending")

    @staticmethod
    async def exists(query_id: str) -> bool:
        """Check if visualization exists for query_id"""
        async with _cache_lock:
            return query_id in _viz_cache

    @staticmethod
    async def clear(query_id: Optional[str] = None) -> None:
        """Clear cache entry(s)"""
        async with _cache_lock:
            if query_id:
                _viz_cache.pop(query_id, None)
                _cache_metadata.pop(query_id, None)
            else:
                _viz_cache.clear()
                _cache_metadata.clear()


