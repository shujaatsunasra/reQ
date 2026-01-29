"""
SemanticDataServer - Handles vector search and embeddings.
"""

from typing import List, Dict, Any, Optional
import time

from core.logging import get_logger
from core.chromadb import semantic_search, get_collection
from .base import MCPServer, MCPRequest, MCPResponse

logger = get_logger(__name__)


class SemanticDataServer(MCPServer):
    """
    MCP Server for semantic search operations.
    
    Handles:
    - Vector similarity search
    - Filter-aware index selection
    - RAG retrieval
    """
    
    def __init__(self):
        super().__init__("semantic")
        self.embedding_model = None  # Will be loaded on demand
    
    def get_operations(self) -> List[str]:
        return [
            "semantic_search",
            "rag_retrieve",
            "text_analysis"
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
            if request.operation == "semantic_search":
                result = await self._semantic_search(request.params)
            elif request.operation == "rag_retrieve":
                result = await self._rag_retrieve(request.params)
            elif request.operation == "text_analysis":
                result = await self._text_analysis(request.params)
            else:
                result = {"data": [], "count": 0}
            
            return self._success_response(
                request.request_id,
                result.get("data"),
                (time.time() - start_time) * 1000,
                {"rows_count": result.get("count", 0)}
            )
            
        except Exception as e:
            self.logger.error(f"Operation {request.operation} failed: {e}")
            return self._error_response(
                request.request_id,
                "EXECUTION_ERROR",
                str(e),
                (time.time() - start_time) * 1000
            )
    
    async def _semantic_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform semantic similarity search.
        """
        query = params.get("query", "")
        top_k = params.get("top_k", 10)
        filters = params.get("filters", {})
        collection_name = params.get("collection", "profiles")
        
        if not query:
            return {"data": [], "count": 0}
        
        # Generate query embedding
        query_embedding = await self._get_embedding(query)
        
        if not query_embedding:
            return {"data": [], "count": 0}
        
        # Select appropriate collection based on filters
        collection_name = self._select_collection(filters)
        
        # Build where filter
        where = None
        if filters:
            where = {}
            if filters.get("data_mode"):
                where["data_mode"] = filters["data_mode"]
            if filters.get("qc_flags"):
                where["qc_flag"] = {"$in": filters["qc_flags"]}
        
        # Perform search
        results = await semantic_search(
            query_embedding=query_embedding,
            collection_name=collection_name,
            n_results=top_k,
            where=where if where else None
        )
        
        return {"data": results, "count": len(results)}
    
    async def _rag_retrieve(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve context for RAG (Retrieval Augmented Generation).
        """
        query = params.get("query", "")
        context_size = params.get("context_size", 5)
        filters = params.get("filters", {})
        
        # First do semantic search
        search_result = await self._semantic_search({
            "query": query,
            "top_k": context_size * 2,
            "filters": filters
        })
        
        if not search_result.get("data"):
            return {"data": {"context": [], "sources": []}, "count": 0}
        
        # Extract and format context
        context = []
        sources = []
        
        for doc in search_result["data"][:context_size]:
            if doc.get("document"):
                context.append(doc["document"])
                sources.append({
                    "id": doc.get("id"),
                    "score": doc.get("score", 0),
                    "metadata": doc.get("metadata", {})
                })
        
        return {
            "data": {
                "context": context,
                "sources": sources,
                "query": query
            },
            "count": len(context)
        }
    
    async def _text_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze text for entities and concepts.
        """
        text = params.get("text", "")
        
        if not text:
            return {"data": {}, "count": 0}
        
        # Basic text analysis (would use spaCy or similar in production)
        analysis = {
            "length": len(text),
            "word_count": len(text.split()),
            "entities": [],
            "concepts": []
        }
        
        # Simple keyword extraction
        oceanographic_terms = [
            "temperature", "salinity", "oxygen", "pressure",
            "depth", "float", "profile", "anomaly", "gradient"
        ]
        
        text_lower = text.lower()
        for term in oceanographic_terms:
            if term in text_lower:
                analysis["concepts"].append(term)
        
        return {"data": analysis, "count": 1}
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using E5 model."""
        try:
            # In production, would use sentence-transformers E5 model
            # For now, return a mock embedding
            import hashlib
            
            # Create deterministic pseudo-embedding from text hash
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            embedding = [
                float(int(text_hash[i:i+2], 16)) / 255.0
                for i in range(0, min(len(text_hash), 768 * 2), 2)
            ]
            
            # Pad to 768 dimensions if needed
            while len(embedding) < 768:
                embedding.append(0.0)
            
            return embedding[:768]
            
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {e}")
            return None
    
    def _select_collection(self, filters: Dict[str, Any]) -> str:
        """
        Select the appropriate ChromaDB collection based on filters.
        Uses filter-aware index selection for better performance.
        """
        # Check for recent data filter
        if filters.get("recent", False):
            return "recent"
        
        # Check for high QC filter
        if filters.get("qc_flags") == [1]:
            return "high_qc"
        
        # Default to main collection
        return "profiles"
