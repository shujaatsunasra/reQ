"""
ChromaDB connection management for vector search.
"""

from typing import Optional, List
import chromadb
from chromadb.config import Settings as ChromaSettings

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

_chroma_client: Optional[chromadb.ClientAPI] = None
_collections: dict = {}


async def init_chromadb() -> bool:
    """Initialize ChromaDB connection. Returns True if successful."""
    global _chroma_client, _collections
    
    try:
        _chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(
                anonymized_telemetry=False
            )
        )
        
        # Create default collection for profile embeddings
        _collections["profiles"] = _chroma_client.get_or_create_collection(
            name="profile_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Create filter-aware collections
        _collections["recent"] = _chroma_client.get_or_create_collection(
            name="recent_6mo_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        
        _collections["high_qc"] = _chroma_client.get_or_create_collection(
            name="high_qc_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info("ChromaDB connection initialized")
        return True
    except Exception as e:
        logger.warning(f"Could not connect to ChromaDB: {e}")
        _chroma_client = None
        return False


def get_chroma() -> Optional[chromadb.ClientAPI]:
    """Get the ChromaDB client instance."""
    return _chroma_client


def get_collection(name: str = "profiles") -> Optional[chromadb.Collection]:
    """Get a ChromaDB collection by name."""
    return _collections.get(name)


async def semantic_search(
    query_embedding: List[float],
    collection_name: str = "profiles",
    n_results: int = 10,
    where: Optional[dict] = None,
    where_document: Optional[dict] = None
) -> List[dict]:
    """
    Perform semantic search on a ChromaDB collection.
    
    Args:
        query_embedding: The query embedding vector
        collection_name: Name of the collection to search
        n_results: Number of results to return
        where: Metadata filter
        where_document: Document content filter
    
    Returns:
        List of matching documents with scores
    """
    collection = get_collection(collection_name)
    if not collection:
        logger.warning(f"Collection {collection_name} not found")
        return []
    
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        documents = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                documents.append({
                    "id": doc_id,
                    "document": results["documents"][0][i] if results["documents"] else None,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else None,
                    "distance": results["distances"][0][i] if results["distances"] else None,
                    "score": 1 - results["distances"][0][i] if results["distances"] else None
                })
        
        return documents
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return []


async def add_embeddings(
    collection_name: str,
    ids: List[str],
    embeddings: List[List[float]],
    documents: Optional[List[str]] = None,
    metadatas: Optional[List[dict]] = None
) -> bool:
    """Add embeddings to a collection."""
    collection = get_collection(collection_name)
    if not collection:
        logger.warning(f"Collection {collection_name} not found")
        return False
    
    try:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        return True
    except Exception as e:
        logger.error(f"Add embeddings error: {e}")
        return False
