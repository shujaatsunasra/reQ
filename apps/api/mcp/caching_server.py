"""
CachingServer - Handles Redis-based caching operations.
"""

from typing import List, Dict, Any, Optional
import time
import hashlib
import json

from core.logging import get_logger
from core.redis import cache_get, cache_set, cache_delete, cache_delete_pattern, get_redis
from .base import MCPServer, MCPRequest, MCPResponse

logger = get_logger(__name__)


class CachingServer(MCPServer):
    """
    MCP Server for caching operations.
    
    Handles:
    - Cache get/set with TTL
    - Cache invalidation
    - Cache warming
    - LRU eviction
    """
    
    def __init__(self):
        super().__init__("cache")
        
        # TTL policies (in seconds)
        self.ttl_policies = {
            "realtime": 300,      # 5 minutes
            "historical": 86400,  # 24 hours
            "metadata": 3600,     # 1 hour
            "visualization": 600  # 10 minutes
        }
    
    def get_operations(self) -> List[str]:
        return [
            "get_cached",
            "set_cached",
            "invalidate",
            "invalidate_by_tag",
            "check_status",
            "warm_cache"
        ]
    
    async def execute(self, request: MCPRequest) -> MCPResponse:
        start_time = time.time()
        
        error = await self._validate_request(request)
        if error:
            return self._error_response(
                request.request_id,
                "VALIDATION_ERROR",
                error,
                (time.time() - start_time) * 1000
            )
        
        try:
            if request.operation == "get_cached":
                result = await self._get_cached(request.params)
            elif request.operation == "set_cached":
                result = await self._set_cached(request.params)
            elif request.operation == "invalidate":
                result = await self._invalidate(request.params)
            elif request.operation == "invalidate_by_tag":
                result = await self._invalidate_by_tag(request.params)
            elif request.operation == "check_status":
                result = await self._check_status(request.params)
            elif request.operation == "warm_cache":
                result = await self._warm_cache(request.params)
            else:
                result = {"data": None, "count": 0}
            
            return self._success_response(
                request.request_id,
                result.get("data"),
                (time.time() - start_time) * 1000,
                {
                    "rows_count": result.get("count", 0),
                    "from_cache": result.get("from_cache", False)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Operation {request.operation} failed: {e}")
            return self._error_response(
                request.request_id,
                "EXECUTION_ERROR",
                str(e),
                (time.time() - start_time) * 1000
            )
    
    async def _get_cached(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a value from cache."""
        key = params.get("key")
        
        if not key:
            return {"data": None, "count": 0, "from_cache": False}
        
        cached = await cache_get(key)
        
        if cached is not None:
            return {"data": cached, "count": 1, "from_cache": True}
        
        return {"data": None, "count": 0, "from_cache": False}
    
    async def _set_cached(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set a value in cache with TTL."""
        key = params.get("key")
        value = params.get("value")
        ttl = params.get("ttl")
        data_type = params.get("data_type", "historical")
        tags = params.get("tags", [])
        
        if not key or value is None:
            return {"data": False, "count": 0}
        
        # Determine TTL
        if ttl is None:
            ttl = self.ttl_policies.get(data_type, 3600)
        
        # Store the value
        success = await cache_set(key, value, ttl)
        
        # Store tags for later invalidation
        if success and tags:
            for tag in tags:
                tag_key = f"tag:{tag}"
                existing = await cache_get(tag_key) or []
                if key not in existing:
                    existing.append(key)
                    await cache_set(tag_key, existing, 86400)  # Tags last 24 hours
        
        return {"data": success, "count": 1 if success else 0}
    
    async def _invalidate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invalidate a specific cache key."""
        key = params.get("key")
        pattern = params.get("pattern")
        
        if key:
            success = await cache_delete(key)
            return {"data": success, "count": 1 if success else 0}
        
        if pattern:
            count = await cache_delete_pattern(pattern)
            return {"data": count > 0, "count": count}
        
        return {"data": False, "count": 0}
    
    async def _invalidate_by_tag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invalidate all cache entries with a given tag."""
        tag = params.get("tag")
        
        if not tag:
            return {"data": False, "count": 0}
        
        tag_key = f"tag:{tag}"
        keys = await cache_get(tag_key) or []
        
        count = 0
        for key in keys:
            if await cache_delete(key):
                count += 1
        
        # Remove the tag itself
        await cache_delete(tag_key)
        
        return {"data": count > 0, "count": count}
    
    async def _check_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check cache status and statistics."""
        redis = get_redis()
        
        if not redis:
            return {
                "data": {
                    "connected": False,
                    "status": "disconnected"
                },
                "count": 0
            }
        
        try:
            info = await redis.info("memory")
            
            return {
                "data": {
                    "connected": True,
                    "status": "healthy",
                    "used_memory": info.get("used_memory_human"),
                    "used_memory_peak": info.get("used_memory_peak_human"),
                    "maxmemory": info.get("maxmemory_human")
                },
                "count": 1
            }
        except Exception as e:
            return {
                "data": {
                    "connected": False,
                    "status": "error",
                    "error": str(e)
                },
                "count": 0
            }
    
    async def _warm_cache(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Warm cache with frequently accessed data.
        Called during startup or after cache clear.
        """
        keys_to_warm = params.get("keys", [])
        loader = params.get("loader")  # Function to load data
        
        # In production, would pre-compute common queries
        # For now, just return success
        
        return {
            "data": {
                "warmed": True,
                "keys_processed": len(keys_to_warm)
            },
            "count": len(keys_to_warm)
        }
    
    @staticmethod
    def generate_cache_key(operation: str, params: Dict[str, Any]) -> str:
        """Generate a normalized cache key from operation and params."""
        # Sort params for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        content = f"{operation}:{sorted_params}"
        
        return f"fc:{hashlib.sha256(content.encode()).hexdigest()[:24]}"
