"""
ChromaDB vector indexer for semantic search.
Indexes float profiles and metadata for natural language queries.
"""

import asyncio
from typing import List, Dict, Any, Optional
import hashlib
import json
from datetime import datetime

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from core.logging import get_logger
from core.config import settings
from .argo_fetcher import ProfileData, FloatMetadata

logger = get_logger(__name__)


class VectorIndexer:
    """Indexes ARGO data into ChromaDB for semantic search."""
    
    def __init__(self):
        self.client: Optional[chromadb.Client] = None
        self.encoder: Optional[SentenceTransformer] = None
        self.profiles_collection = None
        self.floats_collection = None
        self.regions_collection = None
        
    async def connect(self):
        """Initialize ChromaDB client and encoder."""
        # Initialize ChromaDB
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
        
        # Initialize encoder
        self.encoder = SentenceTransformer('intfloat/e5-large-v2')
        
        # Create collections with HNSW indexing
        self.profiles_collection = self.client.get_or_create_collection(
            name="argo_profiles",
            metadata={"hnsw:space": "cosine"},
        )
        
        self.floats_collection = self.client.get_or_create_collection(
            name="argo_floats",
            metadata={"hnsw:space": "cosine"},
        )
        
        self.regions_collection = self.client.get_or_create_collection(
            name="ocean_regions",
            metadata={"hnsw:space": "cosine"},
        )
        
        # Index default regions
        await self._index_default_regions()
        
        logger.info("ChromaDB indexer initialized")
        
    async def _index_default_regions(self):
        """Index ocean region descriptions for semantic matching."""
        regions = [
            {
                "id": "arabian_sea",
                "name": "Arabian Sea",
                "description": "Arabian Sea northwestern Indian Ocean between India and Arabian Peninsula monsoon upwelling warm tropical waters",
                "bounds": {"lat": [5, 25], "lon": [50, 80]},
            },
            {
                "id": "bay_of_bengal",
                "name": "Bay of Bengal",
                "description": "Bay of Bengal northeastern Indian Ocean east of India Bangladesh Myanmar freshwater influx monsoon tropical cyclones",
                "bounds": {"lat": [5, 23], "lon": [80, 100]},
            },
            {
                "id": "north_atlantic",
                "name": "North Atlantic",
                "description": "North Atlantic Ocean Gulf Stream thermohaline circulation deep water formation Labrador Sea subtropical gyre",
                "bounds": {"lat": [20, 60], "lon": [-80, 0]},
            },
            {
                "id": "south_atlantic",
                "name": "South Atlantic",
                "description": "South Atlantic Ocean Benguela Current Brazil Current Antarctic intermediate water subtropical convergence",
                "bounds": {"lat": [-60, 0], "lon": [-70, 20]},
            },
            {
                "id": "north_pacific",
                "name": "North Pacific",
                "description": "North Pacific Ocean Kuroshio Current California Current Pacific Decadal Oscillation subtropical gyre Alaska",
                "bounds": {"lat": [0, 60], "lon": [100, -100]},
            },
            {
                "id": "south_pacific",
                "name": "South Pacific",
                "description": "South Pacific Ocean Humboldt Current South Pacific gyre ENSO El Niño La Niña equatorial upwelling",
                "bounds": {"lat": [-60, 0], "lon": [100, -70]},
            },
            {
                "id": "indian_ocean",
                "name": "Indian Ocean",
                "description": "Indian Ocean tropical warm waters Indonesian throughflow Agulhas Current monsoon circulation Madagascar",
                "bounds": {"lat": [-60, 30], "lon": [20, 120]},
            },
            {
                "id": "southern_ocean",
                "name": "Southern Ocean",
                "description": "Southern Ocean Antarctic Circumpolar Current ACC polar front deep water formation ice shelf Antarctica cold",
                "bounds": {"lat": [-80, -60], "lon": [-180, 180]},
            },
            {
                "id": "mediterranean",
                "name": "Mediterranean Sea",
                "description": "Mediterranean Sea enclosed basin high salinity evaporation Gibraltar Strait Levantine deep water Adriatic",
                "bounds": {"lat": [30, 46], "lon": [-6, 36]},
            },
            {
                "id": "arctic",
                "name": "Arctic Ocean",
                "description": "Arctic Ocean polar ice sea ice Fram Strait Beaufort Gyre Atlantic inflow cold fresh water permafrost",
                "bounds": {"lat": [66, 90], "lon": [-180, 180]},
            },
        ]
        
        # Encode and upsert
        ids = [r["id"] for r in regions]
        documents = [r["description"] for r in regions]
        metadatas = [{
            "name": r["name"],
            "bounds_lat_min": r["bounds"]["lat"][0],
            "bounds_lat_max": r["bounds"]["lat"][1],
            "bounds_lon_min": r["bounds"]["lon"][0],
            "bounds_lon_max": r["bounds"]["lon"][1],
        } for r in regions]
        
        embeddings = self.encoder.encode(documents).tolist()
        
        self.regions_collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        
    def _profile_to_document(self, profile: ProfileData) -> str:
        """Convert profile to searchable document text."""
        # Get basic properties
        lat_hemisphere = "north" if profile.latitude > 0 else "south"
        lon_hemisphere = "east" if profile.longitude > 0 else "west"
        
        # Depth description
        max_depth = max(profile.pressure) if profile.pressure else 0
        depth_desc = "shallow" if max_depth < 500 else "deep" if max_depth > 1500 else "moderate"
        
        # Temperature description
        temps = [t for t in profile.temperature if t is not None]
        if temps:
            avg_temp = sum(temps) / len(temps)
            temp_desc = "cold" if avg_temp < 10 else "warm" if avg_temp > 20 else "temperate"
        else:
            temp_desc = "unknown temperature"
            
        # Salinity description
        sals = [s for s in profile.salinity if s is not None]
        if sals:
            avg_sal = sum(sals) / len(sals)
            sal_desc = "fresh" if avg_sal < 34 else "saline" if avg_sal > 36 else "normal salinity"
        else:
            sal_desc = "unknown salinity"
            
        # Build document
        doc = f"""
        ARGO float {profile.float_id} cycle {profile.cycle_number}
        Location: {abs(profile.latitude):.1f}°{lat_hemisphere} {abs(profile.longitude):.1f}°{lon_hemisphere}
        Date: {profile.timestamp.strftime('%Y-%m-%d')} {profile.timestamp.strftime('%B')}
        {depth_desc} profile reaching {max_depth:.0f} dbar
        {temp_desc} waters with {temp_desc} characteristics
        {sal_desc} water mass
        {len(profile.pressure)} vertical levels measured
        """
        
        # Add BGC info if available
        if profile.oxygen:
            doc += " oxygen measurements biogeochemistry"
        if profile.chlorophyll:
            doc += " chlorophyll phytoplankton biology"
        if profile.nitrate:
            doc += " nitrate nutrients"
            
        return doc.strip()
        
    async def index_profile(self, profile: ProfileData) -> bool:
        """Index a single profile."""
        try:
            doc_id = f"{profile.float_id}_{profile.cycle_number}_{profile.direction}"
            document = self._profile_to_document(profile)
            
            embedding = self.encoder.encode(document).tolist()
            
            metadata = {
                "float_id": profile.float_id,
                "cycle_number": profile.cycle_number,
                "timestamp": profile.timestamp.isoformat(),
                "latitude": profile.latitude,
                "longitude": profile.longitude,
                "max_pressure": max(profile.pressure) if profile.pressure else 0,
                "n_levels": len(profile.pressure),
                "has_oxygen": profile.oxygen is not None,
                "has_chlorophyll": profile.chlorophyll is not None,
            }
            
            self.profiles_collection.upsert(
                ids=[doc_id],
                documents=[document],
                metadatas=[metadata],
                embeddings=[embedding],
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error indexing profile: {e}")
            return False
            
    async def index_float(self, metadata: FloatMetadata) -> bool:
        """Index float metadata."""
        try:
            document = f"""
            ARGO float {metadata.wmo_id}
            Data center: {metadata.dac}
            Institution: {metadata.institution or 'unknown'}
            Project: {metadata.project_name or 'unknown'}
            Principal investigator: {metadata.pi_name or 'unknown'}
            """
            
            embedding = self.encoder.encode(document).tolist()
            
            self.floats_collection.upsert(
                ids=[metadata.wmo_id],
                documents=[document],
                metadatas={
                    "wmo_id": metadata.wmo_id,
                    "dac": metadata.dac,
                    "institution": metadata.institution or "",
                    "project_name": metadata.project_name or "",
                },
                embeddings=[embedding],
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error indexing float: {e}")
            return False
            
    async def search_profiles(
        self, 
        query: str, 
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search profiles by semantic query."""
        try:
            embedding = self.encoder.encode(f"query: {query}").tolist()
            
            where_filter = None
            if filters:
                where_filter = {}
                if "lat_min" in filters:
                    where_filter["latitude"] = {"$gte": filters["lat_min"]}
                if "lat_max" in filters:
                    where_filter["latitude"] = {"$lte": filters["lat_max"]}
                # Add more filters as needed
                    
            results = self.profiles_collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"],
            )
            
            # Format results
            formatted = []
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "similarity": 1 - results["distances"][0][i],
                })
                
            return formatted
            
        except Exception as e:
            logger.error(f"Error searching profiles: {e}")
            return []
            
    async def search_regions(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search for ocean regions by name or description."""
        try:
            embedding = self.encoder.encode(f"query: {query}").tolist()
            
            results = self.regions_collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
            
            formatted = []
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "id": results["ids"][0][i],
                    "name": results["metadatas"][0][i]["name"],
                    "bounds": {
                        "lat": [
                            results["metadatas"][0][i]["bounds_lat_min"],
                            results["metadatas"][0][i]["bounds_lat_max"],
                        ],
                        "lon": [
                            results["metadatas"][0][i]["bounds_lon_min"],
                            results["metadatas"][0][i]["bounds_lon_max"],
                        ],
                    },
                    "similarity": 1 - results["distances"][0][i],
                })
                
            return formatted
            
        except Exception as e:
            logger.error(f"Error searching regions: {e}")
            return []
            
    async def get_stats(self) -> Dict[str, int]:
        """Get indexing statistics."""
        return {
            "profiles": self.profiles_collection.count(),
            "floats": self.floats_collection.count(),
            "regions": self.regions_collection.count(),
        }
