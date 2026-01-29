"""
ARGO Data Ingestion Pipeline
Fetches, parses, and loads ARGO float data from GDAC servers.
"""

import asyncio
import aiohttp
import netCDF4
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, AsyncGenerator
from pathlib import Path
import tempfile
import os
import io

from pydantic import BaseModel
from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)


# GDAC server URLs
GDAC_SERVERS = [
    "https://data-argo.ifremer.fr",
    "ftp://ftp.ifremer.fr/ifremer/argo",
    "ftp://usgodae.org/pub/outgoing/argo",
]


class FloatMetadata(BaseModel):
    """ARGO float metadata."""
    float_id: str
    dac: str  # Data Assembly Center
    wmo_id: str
    cycle_number: int
    position: Dict[str, float]  # lat, lon
    timestamp: datetime
    data_mode: str  # R=realtime, D=delayed, A=adjusted
    institution: Optional[str] = None
    project_name: Optional[str] = None
    pi_name: Optional[str] = None


class ProfileData(BaseModel):
    """Single ARGO profile data."""
    float_id: str
    cycle_number: int
    direction: str  # A=ascending, D=descending
    timestamp: datetime
    latitude: float
    longitude: float
    
    # Measurements (arrays at different pressure levels)
    pressure: List[float]
    temperature: List[Optional[float]]
    salinity: List[Optional[float]]
    
    # QC flags
    pressure_qc: List[int]
    temperature_qc: List[int]
    salinity_qc: List[int]
    
    # Optional BGC parameters
    oxygen: Optional[List[Optional[float]]] = None
    chlorophyll: Optional[List[Optional[float]]] = None
    nitrate: Optional[List[Optional[float]]] = None
    ph: Optional[List[Optional[float]]] = None


class ARGOFetcher:
    """Fetches ARGO data from GDAC servers."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.GDAC_URL or GDAC_SERVERS[0]
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"User-Agent": "FloatChat/1.0"}
        )
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
            
    async def fetch_float_list(self, dac: str = None) -> List[str]:
        """Fetch list of available float WMO IDs."""
        url = f"{self.base_url}/ar_index_global_prof.txt"
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch float list: {response.status}")
                    return []
                    
                content = await response.text()
                lines = content.strip().split('\n')
                
                floats = set()
                for line in lines[1:]:  # Skip header
                    parts = line.split(',')
                    if len(parts) >= 2:
                        float_id = parts[0].split('/')[-1].replace('.nc', '')
                        if dac is None or parts[0].startswith(dac):
                            floats.add(float_id)
                            
                return list(floats)
                
        except Exception as e:
            logger.error(f"Error fetching float list: {e}")
            return []
            
    async def fetch_profile(self, dac: str, wmo_id: str, cycle: int) -> Optional[bytes]:
        """Fetch a single profile NetCDF file."""
        # Try different file patterns
        patterns = [
            f"{dac}/{wmo_id}/profiles/R{wmo_id}_{cycle:03d}.nc",  # Realtime
            f"{dac}/{wmo_id}/profiles/D{wmo_id}_{cycle:03d}.nc",  # Delayed
        ]
        
        for pattern in patterns:
            url = f"{self.base_url}/dac/{pattern}"
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
            except Exception as e:
                logger.debug(f"Failed to fetch {url}: {e}")
                continue
                
        return None
        
    async def fetch_float_meta(self, dac: str, wmo_id: str) -> Optional[FloatMetadata]:
        """Fetch float metadata from meta file."""
        url = f"{self.base_url}/dac/{dac}/{wmo_id}/{wmo_id}_meta.nc"
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                    
                content = await response.read()
                
                # Parse with netCDF4
                with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f:
                    f.write(content)
                    temp_path = f.name
                    
                try:
                    ds = netCDF4.Dataset(temp_path)
                    
                    meta = FloatMetadata(
                        float_id=wmo_id,
                        dac=dac,
                        wmo_id=wmo_id,
                        cycle_number=0,
                        position={"lat": 0, "lon": 0},
                        timestamp=datetime.now(),
                        data_mode="R",
                        institution=self._get_nc_string(ds, 'INSTITUTION'),
                        project_name=self._get_nc_string(ds, 'PROJECT_NAME'),
                        pi_name=self._get_nc_string(ds, 'PI_NAME'),
                    )
                    
                    ds.close()
                    return meta
                    
                finally:
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Error fetching float meta: {e}")
            return None
            
    def _get_nc_string(self, ds, var_name: str) -> Optional[str]:
        """Extract string from NetCDF variable."""
        try:
            if var_name in ds.variables:
                val = ds.variables[var_name][:]
                if hasattr(val, 'tobytes'):
                    return val.tobytes().decode('utf-8').strip()
                return str(val).strip()
        except:
            pass
        return None


class NetCDFParser:
    """Parses ARGO NetCDF files into ProfileData objects."""
    
    @staticmethod
    def parse_profile(content: bytes, float_id: str) -> Optional[ProfileData]:
        """Parse NetCDF profile bytes into ProfileData."""
        
        with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as f:
            f.write(content)
            temp_path = f.name
            
        try:
            ds = netCDF4.Dataset(temp_path)
            
            # Extract dimensions
            n_prof = ds.dimensions['N_PROF'].size
            n_levels = ds.dimensions['N_LEVELS'].size
            
            # Get primary profile (index 0)
            profile_idx = 0
            
            # Position
            lat = float(ds.variables['LATITUDE'][profile_idx])
            lon = float(ds.variables['LONGITUDE'][profile_idx])
            
            # Time
            juld = float(ds.variables['JULD'][profile_idx])
            reference_date = datetime(1950, 1, 1)
            timestamp = reference_date + timedelta(days=juld)
            
            # Cycle number
            cycle = int(ds.variables['CYCLE_NUMBER'][profile_idx])
            
            # Direction
            direction = 'A'  # Default ascending
            if 'DIRECTION' in ds.variables:
                dir_char = ds.variables['DIRECTION'][profile_idx]
                if hasattr(dir_char, 'tobytes'):
                    direction = dir_char.tobytes().decode('utf-8').strip()
                    
            # Measurements
            pres = NetCDFParser._extract_array(ds, 'PRES', profile_idx, n_levels)
            temp = NetCDFParser._extract_array(ds, 'TEMP', profile_idx, n_levels)
            psal = NetCDFParser._extract_array(ds, 'PSAL', profile_idx, n_levels)
            
            # QC flags
            pres_qc = NetCDFParser._extract_qc(ds, 'PRES_QC', profile_idx, n_levels)
            temp_qc = NetCDFParser._extract_qc(ds, 'TEMP_QC', profile_idx, n_levels)
            psal_qc = NetCDFParser._extract_qc(ds, 'PSAL_QC', profile_idx, n_levels)
            
            # Optional BGC parameters
            oxygen = NetCDFParser._extract_array(ds, 'DOXY', profile_idx, n_levels)
            chlorophyll = NetCDFParser._extract_array(ds, 'CHLA', profile_idx, n_levels)
            nitrate = NetCDFParser._extract_array(ds, 'NITRATE', profile_idx, n_levels)
            ph = NetCDFParser._extract_array(ds, 'PH_IN_SITU_TOTAL', profile_idx, n_levels)
            
            ds.close()
            
            # Filter out invalid pressure levels
            valid_indices = [i for i, p in enumerate(pres) if p is not None and p > 0]
            
            profile = ProfileData(
                float_id=float_id,
                cycle_number=cycle,
                direction=direction,
                timestamp=timestamp,
                latitude=lat,
                longitude=lon,
                pressure=[pres[i] for i in valid_indices],
                temperature=[temp[i] for i in valid_indices],
                salinity=[psal[i] for i in valid_indices],
                pressure_qc=[pres_qc[i] for i in valid_indices],
                temperature_qc=[temp_qc[i] for i in valid_indices],
                salinity_qc=[psal_qc[i] for i in valid_indices],
                oxygen=([oxygen[i] for i in valid_indices] if oxygen else None),
                chlorophyll=([chlorophyll[i] for i in valid_indices] if chlorophyll else None),
                nitrate=([nitrate[i] for i in valid_indices] if nitrate else None),
                ph=([ph[i] for i in valid_indices] if ph else None),
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Error parsing NetCDF: {e}")
            return None
            
        finally:
            os.unlink(temp_path)
            
    @staticmethod
    def _extract_array(ds, var_name: str, prof_idx: int, n_levels: int) -> List[Optional[float]]:
        """Extract measurement array from NetCDF."""
        try:
            if var_name not in ds.variables:
                return [None] * n_levels
                
            var = ds.variables[var_name]
            data = var[prof_idx, :]
            
            # Get fill value
            fill_value = getattr(var, '_FillValue', 99999.0)
            
            result = []
            for val in data:
                if np.ma.is_masked(val) or abs(val) > 99990:
                    result.append(None)
                else:
                    result.append(float(val))
                    
            return result
            
        except Exception as e:
            logger.debug(f"Error extracting {var_name}: {e}")
            return [None] * n_levels
            
    @staticmethod
    def _extract_qc(ds, var_name: str, prof_idx: int, n_levels: int) -> List[int]:
        """Extract QC flags from NetCDF."""
        try:
            if var_name not in ds.variables:
                return [9] * n_levels  # 9 = missing
                
            var = ds.variables[var_name]
            data = var[prof_idx, :]
            
            result = []
            for val in data:
                if hasattr(val, 'tobytes'):
                    qc_char = val.tobytes().decode('utf-8').strip()
                    result.append(int(qc_char) if qc_char.isdigit() else 9)
                else:
                    result.append(int(val) if not np.ma.is_masked(val) else 9)
                    
            return result
            
        except Exception as e:
            logger.debug(f"Error extracting QC {var_name}: {e}")
            return [9] * n_levels
