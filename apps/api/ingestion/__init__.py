"""
Data ingestion module for ARGO float data.
"""

from .argo_fetcher import ARGOFetcher, NetCDFParser, ProfileData, FloatMetadata
from .postgres_loader import PostgresLoader
from .vector_indexer import VectorIndexer
from .pipeline import IngestionPipeline

__all__ = [
    "ARGOFetcher",
    "NetCDFParser",
    "ProfileData",
    "FloatMetadata",
    "PostgresLoader",
    "VectorIndexer",
    "IngestionPipeline",
]
