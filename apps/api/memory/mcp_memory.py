"""
MCP Server Memory - Learns from MCP server interactions.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import hashlib

from core.logging import get_logger
from .memory_store import MemoryStore, MemoryEntry

logger = get_logger(__name__)


@dataclass
class ServerPattern:
    """A learned server interaction pattern."""
    server: str
    operation: str
    param_signature: str
    avg_latency: float
    success_rate: float
    cache_hit_rate: float


class MCPServerMemory:
    """
    Memory system for MCP server interactions.
    
    Learns:
    - Server response patterns
    - Optimal parameter configurations
    - Error patterns and recovery strategies
    - Cache effectiveness
    """
    
    def __init__(self):
        self.store = MemoryStore("mcp_server")
        
        # Server performance tracking
        self.server_stats: Dict[str, Dict[str, Any]] = {}
    
    async def record_interaction(
        self,
        server: str,
        operation: str,
        params: Dict[str, Any],
        response_time: float,
        success: bool,
        cache_hit: bool = False,
        error: Optional[str] = None
    ):
        """Record an MCP server interaction."""
        # Generate pattern hash
        param_signature = self._get_param_signature(params)
        pattern_hash = hashlib.sha256(
            f"{server}:{operation}:{param_signature}".encode()
        ).hexdigest()[:16]
        
        entry = MemoryEntry(
            id=f"mcp_{pattern_hash}",
            type="server_interaction",
            content={
                "server": server,
                "operation": operation,
                "param_signature": param_signature,
                "response_time": response_time,
                "success": success,
                "cache_hit": cache_hit,
                "error": error
            },
            success_rate=1.0 if success else 0.0
        )
        
        # Update or store
        existing = await self.store.retrieve(f"mcp_{pattern_hash}")
        if existing:
            # Merge with existing
            await self._merge_interaction(existing, entry)
        else:
            await self.store.store(entry)
        
        # Update server stats
        await self._update_server_stats(
            server, operation, response_time, success, cache_hit
        )
    
    async def get_server_performance(
        self,
        server: str
    ) -> Dict[str, Any]:
        """Get performance statistics for a server."""
        return self.server_stats.get(server, {
            "avg_latency": 0,
            "success_rate": 1.0,
            "cache_hit_rate": 0,
            "request_count": 0
        })
    
    async def get_operation_patterns(
        self,
        server: str,
        operation: str
    ) -> List[ServerPattern]:
        """Get learned patterns for a server operation."""
        # Would search ChromaDB for patterns
        return []
    
    async def get_error_patterns(
        self,
        server: str
    ) -> List[Dict[str, Any]]:
        """Get common error patterns for a server."""
        # Would search for entries with errors
        return []
    
    async def predict_response_time(
        self,
        server: str,
        operation: str,
        params: Dict[str, Any]
    ) -> Optional[float]:
        """Predict response time based on historical data."""
        param_signature = self._get_param_signature(params)
        pattern_hash = hashlib.sha256(
            f"{server}:{operation}:{param_signature}".encode()
        ).hexdigest()[:16]
        
        entry = await self.store.retrieve(f"mcp_{pattern_hash}")
        if entry:
            return entry.content.get("response_time")
        
        # Fall back to server average
        stats = await self.get_server_performance(server)
        return stats.get("avg_latency")
    
    async def should_cache(
        self,
        server: str,
        operation: str,
        params: Dict[str, Any]
    ) -> bool:
        """Determine if an operation result should be cached."""
        stats = await self.get_server_performance(server)
        
        # Cache if high hit rate or slow operation
        if stats.get("cache_hit_rate", 0) > 0.3:
            return True
        if stats.get("avg_latency", 0) > 500:
            return True
        
        return False
    
    async def _merge_interaction(
        self,
        existing: MemoryEntry,
        new: MemoryEntry
    ):
        """Merge new interaction data with existing."""
        # Update with exponential moving average
        alpha = 0.3
        
        old_latency = existing.content.get("response_time", 0)
        new_latency = new.content.get("response_time", 0)
        existing.content["response_time"] = alpha * new_latency + (1 - alpha) * old_latency
        
        # Update success rate
        existing.success_rate = alpha * new.success_rate + (1 - alpha) * existing.success_rate
        
        # Increment request count
        existing.content["request_count"] = existing.content.get("request_count", 0) + 1
        
        await self.store.store(existing)
    
    async def _update_server_stats(
        self,
        server: str,
        operation: str,
        response_time: float,
        success: bool,
        cache_hit: bool
    ):
        """Update aggregate server statistics."""
        if server not in self.server_stats:
            self.server_stats[server] = {
                "avg_latency": response_time,
                "success_rate": 1.0 if success else 0.0,
                "cache_hit_rate": 1.0 if cache_hit else 0.0,
                "request_count": 1
            }
            return
        
        stats = self.server_stats[server]
        n = stats["request_count"]
        
        # Update averages
        stats["avg_latency"] = (stats["avg_latency"] * n + response_time) / (n + 1)
        stats["success_rate"] = (stats["success_rate"] * n + (1 if success else 0)) / (n + 1)
        stats["cache_hit_rate"] = (stats["cache_hit_rate"] * n + (1 if cache_hit else 0)) / (n + 1)
        stats["request_count"] = n + 1
    
    def _get_param_signature(self, params: Dict[str, Any]) -> str:
        """Generate a signature for parameter patterns."""
        # Extract key patterns without specific values
        patterns = []
        
        for key, value in params.items():
            if isinstance(value, list):
                patterns.append(f"{key}:list:{len(value)}")
            elif isinstance(value, dict):
                patterns.append(f"{key}:dict:{len(value)}")
            elif isinstance(value, (int, float)):
                # Bucket numeric values
                if value < 10:
                    patterns.append(f"{key}:num:small")
                elif value < 100:
                    patterns.append(f"{key}:num:medium")
                else:
                    patterns.append(f"{key}:num:large")
            elif isinstance(value, str):
                patterns.append(f"{key}:str:{len(value) // 10}")
            else:
                patterns.append(f"{key}:{type(value).__name__}")
        
        return ",".join(sorted(patterns))
