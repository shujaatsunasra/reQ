"""
Data ingestion pipeline orchestrator.
Coordinates fetching, parsing, loading, and indexing of ARGO data.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time

from core.logging import get_logger
from core.config import settings
from .argo_fetcher import ARGOFetcher, NetCDFParser, ProfileData, FloatMetadata
from .postgres_loader import PostgresLoader
from .vector_indexer import VectorIndexer

logger = get_logger(__name__)


class IngestionPipeline:
    """Orchestrates the full data ingestion pipeline."""
    
    def __init__(self):
        self.fetcher: Optional[ARGOFetcher] = None
        self.loader: Optional[PostgresLoader] = None
        self.indexer: Optional[VectorIndexer] = None
        self.stats = {
            "profiles_fetched": 0,
            "profiles_loaded": 0,
            "profiles_indexed": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }
        
    async def initialize(self):
        """Initialize all pipeline components."""
        logger.info("Initializing ingestion pipeline...")
        
        # Initialize PostgreSQL loader
        self.loader = PostgresLoader()
        await self.loader.connect()
        await self.loader.initialize_schema()
        
        # Initialize vector indexer
        self.indexer = VectorIndexer()
        await self.indexer.connect()
        
        logger.info("Pipeline initialized")
        
    async def shutdown(self):
        """Cleanup pipeline resources."""
        if self.loader:
            await self.loader.disconnect()
            
    async def ingest_float(
        self,
        dac: str,
        wmo_id: str,
        max_cycles: int = None,
        start_cycle: int = 1
    ) -> Dict[str, Any]:
        """Ingest data for a single float."""
        result = {
            "float_id": wmo_id,
            "profiles_ingested": 0,
            "errors": [],
        }
        
        async with ARGOFetcher() as fetcher:
            # Fetch and store float metadata
            meta = await fetcher.fetch_float_meta(dac, wmo_id)
            if meta:
                await self.loader.upsert_float(meta)
                await self.indexer.index_float(meta)
                
            # Fetch profiles
            cycle = start_cycle
            consecutive_failures = 0
            max_failures = 5  # Stop after 5 consecutive missing cycles
            
            while True:
                if max_cycles and cycle > start_cycle + max_cycles:
                    break
                    
                profile_data = await fetcher.fetch_profile(dac, wmo_id, cycle)
                
                if profile_data is None:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        break
                    cycle += 1
                    continue
                    
                consecutive_failures = 0
                
                # Parse profile
                profile = NetCDFParser.parse_profile(profile_data, wmo_id)
                if profile is None:
                    result["errors"].append(f"Failed to parse cycle {cycle}")
                    cycle += 1
                    continue
                    
                # Load to PostgreSQL
                profile_id = await self.loader.insert_profile(profile)
                if profile_id:
                    result["profiles_ingested"] += 1
                    self.stats["profiles_loaded"] += 1
                    
                    # Index to ChromaDB
                    indexed = await self.indexer.index_profile(profile)
                    if indexed:
                        self.stats["profiles_indexed"] += 1
                else:
                    result["errors"].append(f"Failed to load cycle {cycle}")
                    
                cycle += 1
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
        return result
        
    async def ingest_dac(
        self,
        dac: str,
        max_floats: int = None,
        max_cycles_per_float: int = None
    ) -> Dict[str, Any]:
        """Ingest data for all floats from a Data Assembly Center."""
        result = {
            "dac": dac,
            "floats_processed": 0,
            "total_profiles": 0,
            "errors": [],
        }
        
        async with ARGOFetcher() as fetcher:
            float_list = await fetcher.fetch_float_list(dac)
            
            if max_floats:
                float_list = float_list[:max_floats]
                
            logger.info(f"Ingesting {len(float_list)} floats from {dac}")
            
            for wmo_id in float_list:
                try:
                    float_result = await self.ingest_float(
                        dac=dac,
                        wmo_id=wmo_id,
                        max_cycles=max_cycles_per_float
                    )
                    result["floats_processed"] += 1
                    result["total_profiles"] += float_result["profiles_ingested"]
                    result["errors"].extend(float_result["errors"])
                    
                except Exception as e:
                    logger.error(f"Error ingesting float {wmo_id}: {e}")
                    result["errors"].append(f"Float {wmo_id}: {str(e)}")
                    
        return result
        
    async def ingest_region(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        time_start: datetime = None,
        time_end: datetime = None,
    ) -> Dict[str, Any]:
        """Ingest data for a specific geographic region."""
        # This would typically query an index file to find floats in the region
        # For now, return a placeholder
        logger.info(f"Ingesting region: lat [{lat_min}, {lat_max}], lon [{lon_min}, {lon_max}]")
        
        result = {
            "region": {
                "lat": [lat_min, lat_max],
                "lon": [lon_min, lon_max],
            },
            "floats_found": 0,
            "profiles_ingested": 0,
        }
        
        # TODO: Implement region-based ingestion using GDAC index files
        
        return result
        
    async def run_daily_update(self) -> Dict[str, Any]:
        """Run daily incremental update for active floats."""
        self.stats["start_time"] = datetime.now()
        
        result = {
            "floats_updated": 0,
            "new_profiles": 0,
            "errors": [],
        }
        
        # Get list of active floats from database
        db_stats = await self.loader.get_float_stats()
        
        # For each active float, check for new cycles
        # This is a simplified version - production would be more sophisticated
        
        self.stats["end_time"] = datetime.now()
        
        return result
        
    async def compute_derived_properties(self, profile_id: int) -> Dict[str, Any]:
        """Compute and cache derived oceanographic properties for a profile."""
        # This would compute MLD, gradients, anomalies, etc.
        # and store them in the computed_properties table
        
        properties = {}
        
        # Placeholder for actual computations
        # These would use the oceanographic calculation functions
        
        return properties
        
    def get_stats(self) -> Dict[str, Any]:
        """Get current pipeline statistics."""
        return {
            **self.stats,
            "duration_seconds": (
                (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
                if self.stats["start_time"] and self.stats["end_time"]
                else None
            ),
        }


# CLI for running ingestion
async def main():
    """CLI entry point for data ingestion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ARGO Data Ingestion Pipeline")
    parser.add_argument("--dac", help="Data Assembly Center (e.g., 'coriolis', 'aoml')")
    parser.add_argument("--float", help="Single float WMO ID to ingest")
    parser.add_argument("--max-floats", type=int, help="Maximum number of floats to ingest")
    parser.add_argument("--max-cycles", type=int, help="Maximum cycles per float")
    parser.add_argument("--daily-update", action="store_true", help="Run daily incremental update")
    
    args = parser.parse_args()
    
    pipeline = IngestionPipeline()
    await pipeline.initialize()
    
    try:
        if args.daily_update:
            result = await pipeline.run_daily_update()
        elif args.float:
            result = await pipeline.ingest_float(
                dac=args.dac or "coriolis",
                wmo_id=args.float,
                max_cycles=args.max_cycles
            )
        elif args.dac:
            result = await pipeline.ingest_dac(
                dac=args.dac,
                max_floats=args.max_floats,
                max_cycles_per_float=args.max_cycles
            )
        else:
            print("Please specify --dac, --float, or --daily-update")
            return
            
        print(f"Ingestion complete: {result}")
        print(f"Stats: {pipeline.get_stats()}")
        
    finally:
        await pipeline.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
