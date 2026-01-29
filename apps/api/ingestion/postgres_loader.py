"""
PostgreSQL data loader for ARGO data.
Handles database insertion with PostGIS spatial indexing.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncpg
import json

from core.logging import get_logger
from core.config import settings
from .argo_fetcher import ProfileData, FloatMetadata

logger = get_logger(__name__)


class PostgresLoader:
    """Loads ARGO data into PostgreSQL with PostGIS."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self):
        """Initialize connection pool."""
        self.pool = await asyncpg.create_pool(
            host=settings.SUPABASE_HOST,
            port=settings.SUPABASE_PORT,
            user=settings.SUPABASE_USER,
            password=settings.SUPABASE_PASSWORD,
            database=settings.SUPABASE_DB,
            min_size=2,
            max_size=10,
        )
        
    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            
    async def initialize_schema(self):
        """Create database tables and indexes."""
        schema_sql = """
        -- Enable PostGIS
        CREATE EXTENSION IF NOT EXISTS postgis;
        
        -- Float metadata table
        CREATE TABLE IF NOT EXISTS floats (
            id SERIAL PRIMARY KEY,
            wmo_id VARCHAR(20) UNIQUE NOT NULL,
            dac VARCHAR(20) NOT NULL,
            institution VARCHAR(100),
            project_name VARCHAR(200),
            pi_name VARCHAR(100),
            deploy_date TIMESTAMP,
            last_update TIMESTAMP DEFAULT NOW(),
            total_cycles INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Profiles table
        CREATE TABLE IF NOT EXISTS profiles (
            id SERIAL PRIMARY KEY,
            float_id VARCHAR(20) NOT NULL REFERENCES floats(wmo_id),
            cycle_number INTEGER NOT NULL,
            direction CHAR(1) DEFAULT 'A',
            timestamp TIMESTAMP NOT NULL,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            position GEOGRAPHY(Point, 4326),
            data_mode CHAR(1) DEFAULT 'R',
            n_levels INTEGER,
            max_pressure FLOAT,
            created_at TIMESTAMP DEFAULT NOW(),
            
            UNIQUE(float_id, cycle_number, direction)
        );
        
        -- Measurements table (normalized for efficient queries)
        CREATE TABLE IF NOT EXISTS measurements (
            id BIGSERIAL PRIMARY KEY,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            level_index SMALLINT NOT NULL,
            pressure FLOAT NOT NULL,
            temperature FLOAT,
            salinity FLOAT,
            oxygen FLOAT,
            chlorophyll FLOAT,
            nitrate FLOAT,
            ph FLOAT,
            pressure_qc SMALLINT DEFAULT 9,
            temperature_qc SMALLINT DEFAULT 9,
            salinity_qc SMALLINT DEFAULT 9,
            
            UNIQUE(profile_id, level_index)
        );
        
        -- Computed properties table (for caching computed values)
        CREATE TABLE IF NOT EXISTS computed_properties (
            id SERIAL PRIMARY KEY,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            property_name VARCHAR(50) NOT NULL,
            property_value JSONB NOT NULL,
            computed_at TIMESTAMP DEFAULT NOW(),
            
            UNIQUE(profile_id, property_name)
        );
        
        -- Regions lookup table
        CREATE TABLE IF NOT EXISTS regions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            display_name VARCHAR(200),
            bounds GEOGRAPHY(Polygon, 4326),
            metadata JSONB
        );
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_profiles_float_id ON profiles(float_id);
        CREATE INDEX IF NOT EXISTS idx_profiles_timestamp ON profiles(timestamp);
        CREATE INDEX IF NOT EXISTS idx_profiles_position ON profiles USING GIST(position);
        CREATE INDEX IF NOT EXISTS idx_measurements_profile ON measurements(profile_id);
        CREATE INDEX IF NOT EXISTS idx_measurements_pressure ON measurements(pressure);
        CREATE INDEX IF NOT EXISTS idx_floats_dac ON floats(dac);
        CREATE INDEX IF NOT EXISTS idx_floats_status ON floats(status);
        
        -- Insert default regions
        INSERT INTO regions (name, display_name, bounds) VALUES
        ('arabian_sea', 'Arabian Sea', ST_GeogFromText('POLYGON((50 5, 80 5, 80 25, 50 25, 50 5))')),
        ('bay_of_bengal', 'Bay of Bengal', ST_GeogFromText('POLYGON((80 5, 100 5, 100 23, 80 23, 80 5))')),
        ('north_atlantic', 'North Atlantic', ST_GeogFromText('POLYGON((-80 20, 0 20, 0 60, -80 60, -80 20))')),
        ('south_atlantic', 'South Atlantic', ST_GeogFromText('POLYGON((-70 -60, 20 -60, 20 0, -70 0, -70 -60))')),
        ('north_pacific', 'North Pacific', ST_GeogFromText('POLYGON((100 0, -100 0, -100 60, 100 60, 100 0))')),
        ('south_pacific', 'South Pacific', ST_GeogFromText('POLYGON((100 -60, -70 -60, -70 0, 100 0, 100 -60))')),
        ('indian_ocean', 'Indian Ocean', ST_GeogFromText('POLYGON((20 -60, 120 -60, 120 30, 20 30, 20 -60))')),
        ('southern_ocean', 'Southern Ocean', ST_GeogFromText('POLYGON((-180 -80, 180 -80, 180 -60, -180 -60, -180 -80))'))
        ON CONFLICT (name) DO NOTHING;
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(schema_sql)
            
        logger.info("Database schema initialized")
        
    async def upsert_float(self, metadata: FloatMetadata) -> bool:
        """Insert or update float metadata."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO floats (wmo_id, dac, institution, project_name, pi_name, last_update)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (wmo_id) DO UPDATE SET
                        dac = EXCLUDED.dac,
                        institution = COALESCE(EXCLUDED.institution, floats.institution),
                        project_name = COALESCE(EXCLUDED.project_name, floats.project_name),
                        pi_name = COALESCE(EXCLUDED.pi_name, floats.pi_name),
                        last_update = NOW()
                """, metadata.wmo_id, metadata.dac, metadata.institution, 
                    metadata.project_name, metadata.pi_name)
                    
            return True
            
        except Exception as e:
            logger.error(f"Error upserting float {metadata.wmo_id}: {e}")
            return False
            
    async def insert_profile(self, profile: ProfileData) -> Optional[int]:
        """Insert a profile and its measurements. Returns profile ID."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Insert profile
                    profile_id = await conn.fetchval("""
                        INSERT INTO profiles (
                            float_id, cycle_number, direction, timestamp,
                            latitude, longitude, position, n_levels, max_pressure
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, 
                                ST_SetSRID(ST_MakePoint($6, $5), 4326)::geography,
                                $7, $8)
                        ON CONFLICT (float_id, cycle_number, direction) 
                        DO UPDATE SET
                            timestamp = EXCLUDED.timestamp,
                            latitude = EXCLUDED.latitude,
                            longitude = EXCLUDED.longitude,
                            position = EXCLUDED.position,
                            n_levels = EXCLUDED.n_levels,
                            max_pressure = EXCLUDED.max_pressure
                        RETURNING id
                    """, profile.float_id, profile.cycle_number, profile.direction,
                        profile.timestamp, profile.latitude, profile.longitude,
                        len(profile.pressure), max(profile.pressure) if profile.pressure else None)
                    
                    # Delete existing measurements for this profile
                    await conn.execute(
                        "DELETE FROM measurements WHERE profile_id = $1",
                        profile_id
                    )
                    
                    # Insert measurements
                    measurements = []
                    for i, pres in enumerate(profile.pressure):
                        measurements.append((
                            profile_id,
                            i,
                            pres,
                            profile.temperature[i] if i < len(profile.temperature) else None,
                            profile.salinity[i] if i < len(profile.salinity) else None,
                            profile.oxygen[i] if profile.oxygen and i < len(profile.oxygen) else None,
                            profile.chlorophyll[i] if profile.chlorophyll and i < len(profile.chlorophyll) else None,
                            profile.nitrate[i] if profile.nitrate and i < len(profile.nitrate) else None,
                            profile.ph[i] if profile.ph and i < len(profile.ph) else None,
                            profile.pressure_qc[i] if i < len(profile.pressure_qc) else 9,
                            profile.temperature_qc[i] if i < len(profile.temperature_qc) else 9,
                            profile.salinity_qc[i] if i < len(profile.salinity_qc) else 9,
                        ))
                        
                    await conn.executemany("""
                        INSERT INTO measurements (
                            profile_id, level_index, pressure, temperature, salinity,
                            oxygen, chlorophyll, nitrate, ph,
                            pressure_qc, temperature_qc, salinity_qc
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """, measurements)
                    
                    # Update float cycle count
                    await conn.execute("""
                        UPDATE floats SET 
                            total_cycles = (
                                SELECT COUNT(DISTINCT cycle_number) 
                                FROM profiles WHERE float_id = $1
                            ),
                            last_update = NOW()
                        WHERE wmo_id = $1
                    """, profile.float_id)
                    
            return profile_id
            
        except Exception as e:
            logger.error(f"Error inserting profile {profile.float_id}/{profile.cycle_number}: {e}")
            return None
            
    async def batch_insert_profiles(self, profiles: List[ProfileData]) -> Dict[str, int]:
        """Insert multiple profiles. Returns counts of success/failure."""
        success = 0
        failed = 0
        
        for profile in profiles:
            result = await self.insert_profile(profile)
            if result:
                success += 1
            else:
                failed += 1
                
        return {"success": success, "failed": failed}
        
    async def get_float_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded data."""
        async with self.pool.acquire() as conn:
            stats = {}
            
            stats['total_floats'] = await conn.fetchval(
                "SELECT COUNT(*) FROM floats"
            )
            stats['active_floats'] = await conn.fetchval(
                "SELECT COUNT(*) FROM floats WHERE status = 'active'"
            )
            stats['total_profiles'] = await conn.fetchval(
                "SELECT COUNT(*) FROM profiles"
            )
            stats['total_measurements'] = await conn.fetchval(
                "SELECT COUNT(*) FROM measurements"
            )
            stats['date_range'] = await conn.fetchrow(
                "SELECT MIN(timestamp) as min_date, MAX(timestamp) as max_date FROM profiles"
            )
            stats['dac_counts'] = dict(await conn.fetch(
                "SELECT dac, COUNT(*) as count FROM floats GROUP BY dac"
            ))
            
        return stats
