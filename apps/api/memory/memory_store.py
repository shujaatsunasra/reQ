"""
Memory Store - Base storage for memory systems.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json

from core.logging import get_logger
from core.redis import cache_get, cache_set, cache_delete
from core.chromadb import get_collection

logger = get_logger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    type: str
    content: Dict[str, Any]
    embedding: Optional[List[float]] = None
    timestamp: str = ""
    access_count: int = 0
    success_rate: float = 1.0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class MemoryStore:
    """
    Base storage layer for memory systems.
    
    Provides:
    - Redis-based short-term memory
    - ChromaDB-based long-term vector memory
    - Access patterns for retrieval
    """
    
    def __init__(self, name: str):
        self.name = name
        self.collection_name = f"memory_{name}"
        self.redis_prefix = f"mem:{name}:"
        
        # LRU parameters
        self.max_entries = 10000
        self.ttl_short = 3600  # 1 hour
        self.ttl_long = 86400 * 7  # 7 days
    
    async def store(
        self,
        entry: MemoryEntry,
        long_term: bool = False
    ) -> bool:
        """Store a memory entry."""
        try:
            # Store in Redis (short-term)
            key = f"{self.redis_prefix}{entry.id}"
            ttl = self.ttl_long if long_term else self.ttl_short
            
            await cache_set(
                key,
                {
                    "id": entry.id,
                    "type": entry.type,
                    "content": entry.content,
                    "timestamp": entry.timestamp,
                    "access_count": entry.access_count,
                    "success_rate": entry.success_rate,
                    "metadata": entry.metadata
                },
                ttl
            )
            
            # Store in ChromaDB if long-term
            if long_term and entry.embedding:
                collection = get_collection(self.collection_name)
                if collection:
                    collection.add(
                        ids=[entry.id],
                        embeddings=[entry.embedding],
                        documents=[json.dumps(entry.content)],
                        metadatas=[{
                            "type": entry.type,
                            "timestamp": entry.timestamp,
                            "success_rate": entry.success_rate,
                            **(entry.metadata or {})
                        }]
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Memory store failed: {e}")
            return False
    
    async def retrieve(
        self,
        entry_id: str
    ) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        try:
            key = f"{self.redis_prefix}{entry_id}"
            data = await cache_get(key)
            
            if data:
                # Update access count
                data["access_count"] = data.get("access_count", 0) + 1
                await cache_set(key, data, self.ttl_short)
                
                return MemoryEntry(
                    id=data["id"],
                    type=data["type"],
                    content=data["content"],
                    timestamp=data.get("timestamp", ""),
                    access_count=data.get("access_count", 0),
                    success_rate=data.get("success_rate", 1.0),
                    metadata=data.get("metadata")
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Memory retrieve failed: {e}")
            return None
    
    async def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        filter_type: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Search memory using vector similarity."""
        try:
            collection = get_collection(self.collection_name)
            if not collection:
                return []
            
            where = {"type": filter_type} if filter_type else None
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
            
            entries = []
            if results and results["ids"]:
                for i, id in enumerate(results["ids"][0]):
                    doc = results["documents"][0][i] if results["documents"] else "{}"
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    
                    entries.append(MemoryEntry(
                        id=id,
                        type=meta.get("type", "unknown"),
                        content=json.loads(doc) if isinstance(doc, str) else doc,
                        timestamp=meta.get("timestamp", ""),
                        success_rate=meta.get("success_rate", 1.0),
                        metadata=meta
                    ))
            
            return entries
            
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []
    
    async def update_success_rate(
        self,
        entry_id: str,
        success: bool
    ) -> bool:
        """Update success rate for a memory entry."""
        try:
            entry = await self.retrieve(entry_id)
            if not entry:
                return False
            
            # Exponential moving average
            alpha = 0.3
            new_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * entry.success_rate
            entry.success_rate = new_rate
            
            return await self.store(entry)
            
        except Exception as e:
            logger.error(f"Update success rate failed: {e}")
            return False
    
    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        try:
            key = f"{self.redis_prefix}{entry_id}"
            await cache_delete(key)
            
            collection = get_collection(self.collection_name)
            if collection:
                collection.delete(ids=[entry_id])
            
            return True
            
        except Exception as e:
            logger.error(f"Memory delete failed: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics."""
        try:
            collection = get_collection(self.collection_name)
            count = collection.count() if collection else 0
            
            return {
                "name": self.name,
                "collection": self.collection_name,
                "entry_count": count,
                "max_entries": self.max_entries
            }
            
        except Exception:
            return {
                "name": self.name,
                "collection": self.collection_name,
                "entry_count": 0,
                "max_entries": self.max_entries
            }
