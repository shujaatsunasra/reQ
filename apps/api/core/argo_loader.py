"""
ARGO Data Loader - Reads real ARGO NetCDF data from local directory

This module provides functions to load and query ARGO float data from 
the local data-set directory containing NetCDF files and index files.

Supports multiple datasets automatically:
- argo_data_2019
- argo_data_2020
- argo_data_2021
- etc.

Just add a new folder with the naming convention "argo_data_YYYY" and it
will be automatically detected and included in queries.
"""

import os
import csv
import logging
import random
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


def find_netcdf_file(profile: Dict[str, Any]) -> Optional[Path]:
    """
    Find the actual NetCDF file for a profile based on index metadata.
    
    The index file_path is like: data/indian/2019/01/nodc_D1901786_156.nc
    But actual files are named like: 01_nodc_D1901786_156.nc (with month prefix)
    
    Args:
        profile: Profile dict with file_path, month, year
        
    Returns:
        Path to NetCDF file if found, None otherwise
    """
    datasets = scan_datasets()
    year = profile.get('year', 2019)
    month = profile.get('month', 1)
    file_path = profile.get('file_path', '')
    
    if not file_path:
        return None
    
    # Extract just the filename from the path
    # file_path format: data/indian/2019/01/nodc_D1901786_156.nc
    filename = os.path.basename(file_path)  # nodc_D1901786_156.nc
    
    # Try to find in the netcdf_files directory with month prefix
    year_key = str(year)
    if year_key not in datasets:
        return None
    
    netcdf_dir = datasets[year_key].get("netcdf_dir")
    if not netcdf_dir or not netcdf_dir.exists():
        return None
    
    # Try exact match with month prefix: 01_nodc_D1901786_156.nc
    month_prefix = f"{month:02d}_"
    candidate = netcdf_dir / f"{month_prefix}{filename}"
    if candidate.exists():
        return candidate
    
    # Try without month prefix
    candidate = netcdf_dir / filename
    if candidate.exists():
        return candidate
    
    # Try glob search for the float ID and cycle
    # Extract float_id from filename like nodc_D1901786_156.nc -> 1901786
    import re
    match = re.search(r'nodc_[DR](\d+)_(\d+)', filename)
    if match:
        float_id = match.group(1)
        cycle = match.group(2)
        # Search for any file matching this pattern
        pattern = f"*nodc_*{float_id}_{cycle}.nc"
        matches = list(netcdf_dir.glob(pattern))
        if matches:
            return matches[0]
    
    return None


def load_real_netcdf_data(nc_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load actual measurement data from a NetCDF file.
    
    Args:
        nc_path: Path to the NetCDF file
        
    Returns:
        Dict with temperature, salinity, depth, QC flags, profiles
    """
    try:
        import netCDF4 as nc
    except ImportError:
        logger.warning("netCDF4 not installed - cannot load real data")
        return None
    
    try:
        ds = nc.Dataset(str(nc_path))
        
        # Get data mode (R=real-time, A=adjusted, D=delayed)
        data_mode = 'R'
        if 'data_mode' in ds.variables:
            dm = ds.variables['data_mode'][:]
            if hasattr(dm, 'tobytes'):
                data_mode = dm.tobytes().decode().strip()[0] if dm.tobytes() else 'R'
            elif len(dm) > 0:
                data_mode = str(dm[0])
        
        # Prefer adjusted data if available (D mode)
        use_adjusted = data_mode in ['A', 'D']
        
        # Extract temperature
        temp_var = 'temp_adjusted' if (use_adjusted and 'temp_adjusted' in ds.variables) else 'temp'
        if temp_var in ds.variables:
            temp_data = ds.variables[temp_var][0, :].data if len(ds.variables[temp_var].shape) > 1 else ds.variables[temp_var][:].data
            temp_data = np.where((temp_data > 50) | (temp_data < -5), np.nan, temp_data)
        else:
            temp_data = np.array([np.nan])
        
        # Extract salinity
        psal_var = 'psal_adjusted' if (use_adjusted and 'psal_adjusted' in ds.variables) else 'psal'
        if psal_var in ds.variables:
            psal_data = ds.variables[psal_var][0, :].data if len(ds.variables[psal_var].shape) > 1 else ds.variables[psal_var][:].data
            psal_data = np.where((psal_data > 50) | (psal_data < 0), np.nan, psal_data)
        else:
            psal_data = np.array([np.nan])
        
        # Extract pressure/depth
        pres_var = 'pres_adjusted' if (use_adjusted and 'pres_adjusted' in ds.variables) else 'pres'
        if pres_var in ds.variables:
            pres_data = ds.variables[pres_var][0, :].data if len(ds.variables[pres_var].shape) > 1 else ds.variables[pres_var][:].data
            pres_data = np.where(pres_data > 10000, np.nan, pres_data)
        else:
            pres_data = np.array([np.nan])
        
        # Extract QC flags
        qc_temp = 1  # Default to good
        if 'temp_qc' in ds.variables:
            qc_data = ds.variables['temp_qc'][0, :] if len(ds.variables['temp_qc'].shape) > 1 else ds.variables['temp_qc'][:]
            if hasattr(qc_data, 'tobytes'):
                qc_str = qc_data.tobytes().decode()
                qc_temp = int(qc_str[0]) if qc_str and qc_str[0].isdigit() else 1
            elif len(qc_data) > 0:
                qc_temp = int(qc_data[0]) if qc_data[0] != b'' else 1
        
        qc_psal = 1
        if 'psal_qc' in ds.variables:
            qc_data = ds.variables['psal_qc'][0, :] if len(ds.variables['psal_qc'].shape) > 1 else ds.variables['psal_qc'][:]
            if hasattr(qc_data, 'tobytes'):
                qc_str = qc_data.tobytes().decode()
                qc_psal = int(qc_str[0]) if qc_str and qc_str[0].isdigit() else 1
        
        qc_pres = 1
        if 'pres_qc' in ds.variables:
            qc_data = ds.variables['pres_qc'][0, :] if len(ds.variables['pres_qc'].shape) > 1 else ds.variables['pres_qc'][:]
            if hasattr(qc_data, 'tobytes'):
                qc_str = qc_data.tobytes().decode()
                qc_pres = int(qc_str[0]) if qc_str and qc_str[0].isdigit() else 1
        
        ds.close()
        
        # Calculate surface values (mean of top 10 levels or available)
        valid_temp = temp_data[~np.isnan(temp_data)]
        valid_psal = psal_data[~np.isnan(psal_data)]
        valid_pres = pres_data[~np.isnan(pres_data)]
        
        surface_temp = float(np.mean(valid_temp[:10])) if len(valid_temp) > 0 else None
        surface_sal = float(np.mean(valid_psal[:10])) if len(valid_psal) > 0 else None
        max_depth = float(np.max(valid_pres)) if len(valid_pres) > 0 else None
        
        return {
            'temperature': round(surface_temp, 2) if surface_temp else None,
            'salinity': round(surface_sal, 2) if surface_sal else None,
            'depth': round(max_depth, 1) if max_depth else None,
            'qc_flag': qc_temp,
            'qc_temp': qc_temp,
            'qc_psal': qc_psal,
            'qc_pres': qc_pres,
            'data_mode': data_mode,
            'temperature_profile': [round(float(t), 2) for t in valid_temp.tolist()[:100]],
            'salinity_profile': [round(float(s), 2) for s in valid_psal.tolist()[:100]],
            'pressure_profile': [round(float(p), 1) for p in valid_pres.tolist()[:100]],
            'n_levels': len(valid_temp),
            'source_file': str(nc_path),
            'data_source': 'netcdf',
        }
        
    except Exception as e:
        logger.warning(f"Error reading NetCDF {nc_path}: {e}")
        return None


def enrich_profile_with_measurements(profile: Dict[str, Any], load_netcdf: bool = True) -> Dict[str, Any]:
    """
    Enrich a profile with REAL measurement data from NetCDF files.
    
    Loads actual temperature, salinity, and QC flags from the local NetCDF dataset.
    
    Args:
        profile: The profile dict from index files
        load_netcdf: If True (default), load real data from NetCDF files
        
    Returns:
        Profile dict enriched with real temperature, salinity, depth, qc_flag, data_mode
    """
    enriched = profile.copy()
    
    # Try to find and load real NetCDF data
    nc_path = find_netcdf_file(profile)
    
    if nc_path:
        real_data = load_real_netcdf_data(nc_path)
        if real_data:
            enriched.update(real_data)
            return enriched
    
    # If no NetCDF found, mark as missing but use index depth
    enriched.update({
        'temperature': None,
        'salinity': None,
        'depth': profile.get('depth_max'),
        'qc_flag': 9,  # 9 = missing value
        'qc_temp': 9,
        'qc_psal': 9,
        'qc_pres': 9,
        'data_mode': 'M',  # M = missing
        'temperature_profile': [],
        'salinity_profile': [],
        'pressure_profile': [],
        'n_levels': 0,
        'data_source': 'missing',
    })
    
    return enriched

# Data directory path - relative to project root
DATA_ROOT = Path(__file__).parent.parent.parent.parent / "data-set"

# Cache for loaded data
_datasets_cache: Dict[str, Dict] = {}  # {year: {index_cache, netcdf_dir, ...}}
_all_profiles_cache: Optional[List[Dict]] = None
_last_scan_time: Optional[float] = None
CACHE_TTL_SECONDS = 300  # Re-scan for new datasets every 5 minutes


def get_data_root() -> Path:
    """Get the root path to the data-set directory."""
    return DATA_ROOT


def scan_datasets() -> Dict[str, Dict]:
    """
    Scan for all available ARGO datasets (argo_data_YYYY folders).
    
    Returns:
        Dict mapping year to dataset info
    """
    global _datasets_cache, _last_scan_time
    
    import time
    current_time = time.time()
    
    # Use cache if recent
    if _last_scan_time and (current_time - _last_scan_time) < CACHE_TTL_SECONDS:
        if _datasets_cache:
            return _datasets_cache
    
    datasets = {}
    
    if not DATA_ROOT.exists():
        logger.warning(f"Data root directory not found: {DATA_ROOT}")
        return datasets
    
    # Scan for argo_data_* folders
    for folder in DATA_ROOT.iterdir():
        if folder.is_dir() and folder.name.startswith("argo_data_"):
            try:
                year = folder.name.replace("argo_data_", "")
                if year.isdigit():
                    year_int = int(year)
                    
                    index_dir = folder / "index_files"
                    netcdf_dir = folder / "netcdf_files"
                    metadata_file = folder / "metadata" / "download_summary.txt"
                    
                    # Count available files
                    index_files = list(index_dir.glob("*.txt")) if index_dir.exists() else []
                    netcdf_files = list(netcdf_dir.glob("*.nc")) if netcdf_dir.exists() else []
                    
                    datasets[year] = {
                        "year": year_int,
                        "path": folder,
                        "index_dir": index_dir,
                        "netcdf_dir": netcdf_dir,
                        "metadata_file": metadata_file,
                        "index_file_count": len(index_files),
                        "netcdf_file_count": len(netcdf_files),
                        "available": len(index_files) > 0,
                    }
                    
                    logger.info(f"Found dataset: argo_data_{year} ({len(index_files)} index files, {len(netcdf_files)} NetCDF files)")
                    
            except Exception as e:
                logger.error(f"Error scanning dataset folder {folder}: {e}")
    
    _datasets_cache = datasets
    _last_scan_time = current_time
    
    logger.info(f"Total datasets found: {len(datasets)} ({', '.join(sorted(datasets.keys()))})")
    return datasets


def get_available_years() -> List[int]:
    """
    Get list of available years in the dataset.
    
    Returns:
        Sorted list of years (e.g., [2019, 2020, 2021])
    """
    datasets = scan_datasets()
    return sorted([d["year"] for d in datasets.values() if d["available"]])


def get_dataset_info() -> Dict[str, Any]:
    """
    Get summary information about all available datasets.
    
    Returns:
        Dict with dataset summary
    """
    datasets = scan_datasets()
    
    total_index = sum(d["index_file_count"] for d in datasets.values())
    total_netcdf = sum(d["netcdf_file_count"] for d in datasets.values())
    
    return {
        "data_root": str(DATA_ROOT),
        "datasets": list(datasets.keys()),
        "years": get_available_years(),
        "total_index_files": total_index,
        "total_netcdf_files": total_netcdf,
        "dataset_details": {
            year: {
                "year": info["year"],
                "index_files": info["index_file_count"],
                "netcdf_files": info["netcdf_file_count"],
                "available": info["available"],
            }
            for year, info in datasets.items()
        }
    }


def load_index_files(
    months: Optional[List[int]] = None,
    years: Optional[List[int]] = None,
) -> List[Dict]:
    """
    Load ARGO index files into memory from all available datasets.
    
    Args:
        months: Optional list of months (1-12) to load. If None, loads all.
        years: Optional list of years to load. If None, loads all available.
        
    Returns:
        List of profile metadata dictionaries.
    """
    global _all_profiles_cache
    
    datasets = scan_datasets()
    
    if not datasets:
        logger.warning("No ARGO datasets found")
        return []
    
    # Filter years if specified
    if years:
        datasets = {k: v for k, v in datasets.items() if v["year"] in years}
    
    profiles = []
    
    for year_key, dataset_info in datasets.items():
        if not dataset_info["available"]:
            continue
            
        index_dir = dataset_info["index_dir"]
        year_val = dataset_info["year"]
        
        months_to_load = months if months else list(range(1, 13))
        
        for month in months_to_load:
            index_file = index_dir / f"index_{month:02d}_{year_val}.txt"
            if not index_file.exists():
                continue
                
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        profiles.append({
                            'float_id': row['floatID'],
                            'data_center': row['data_center'],
                            'file_path': row['file_path'],
                            'timestamp': row['date_time_min'],
                            'date': row['date_time_min'][:10] if row['date_time_min'] else None,
                            'latitude': float(row['latitude_min']),
                            'longitude': float(row['longitude_min']),
                            'depth_min': float(row['depth_min']),
                            'depth_max': float(row['depth_max']),
                            'month': month,
                            'year': year_val,
                            'dataset': f"argo_data_{year_val}",
                        })
            except Exception as e:
                logger.error(f"Error loading index file {index_file}: {e}")
    
    logger.info(f"Loaded {len(profiles)} profiles from {len(datasets)} datasets")
    return profiles


def query_profiles(
    region: Optional[str] = None,
    bbox: Optional[List[float]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    float_ids: Optional[List[str]] = None,
    depth_min: Optional[float] = None,
    depth_max: Optional[float] = None,
    months: Optional[List[int]] = None,
    years: Optional[List[int]] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Query ARGO profiles from index files with filtering.
    
    Args:
        region: Named region (e.g., 'arabian sea', 'indian ocean')
        bbox: Bounding box [lon_min, lat_min, lon_max, lat_max]
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        float_ids: List of specific float IDs to filter
        depth_min: Minimum depth
        depth_max: Maximum depth
        months: Specific months to query
        years: Specific years to query (e.g., [2019, 2020])
        limit: Maximum results to return
        offset: Offset for pagination
        
    Returns:
        Dict with profiles, stats, and metadata
    """
    # Load index data
    profiles = load_index_files(months, years)
    
    # Detect region from query
    region_detected = None
    if region:
        region_lower = region.lower()
        bbox, region_detected = get_region_bbox(region_lower)
    
    # Apply filters
    filtered = []
    for p in profiles:
        # Bounding box filter
        if bbox:
            lon_min, lat_min, lon_max, lat_max = bbox
            if not (lon_min <= p['longitude'] <= lon_max and lat_min <= p['latitude'] <= lat_max):
                continue
        
        # Date filter
        if start_date and p['date'] and p['date'] < start_date:
            continue
        if end_date and p['date'] and p['date'] > end_date:
            continue
        
        # Float ID filter
        if float_ids and p['float_id'] not in float_ids:
            continue
        
        # Depth filter
        if depth_min is not None and p['depth_max'] < depth_min:
            continue
        if depth_max is not None and p['depth_min'] > depth_max:
            continue
        
        filtered.append(p)
    
    total_count = len(filtered)
    
    # Apply pagination
    paginated = filtered[offset:offset + limit]
    
    # Enrich profiles with measurement data (temperature, salinity, QC flags)
    enriched_profiles = [enrich_profile_with_measurements(p) for p in paginated]
    
    # Calculate stats including measurement data
    if enriched_profiles:
        lats = [p['latitude'] for p in enriched_profiles]
        lons = [p['longitude'] for p in enriched_profiles]
        depths = [p['depth_max'] for p in enriched_profiles]
        temps = [p['temperature'] for p in enriched_profiles if p.get('temperature')]
        sals = [p['salinity'] for p in enriched_profiles if p.get('salinity')]
        unique_floats = set(p['float_id'] for p in enriched_profiles)
        unique_years = set(p['year'] for p in enriched_profiles)
        datasets_used = set(p['dataset'] for p in enriched_profiles)
        
        # QC stats
        qc_flags = [p.get('qc_flag', 0) for p in enriched_profiles]
        good_count = sum(1 for qc in qc_flags if qc in [1, 2])
        flagged_count = sum(1 for qc in qc_flags if qc in [3, 4])
        
        stats = {
            'total_profiles': total_count,
            'returned_profiles': len(enriched_profiles),
            'unique_floats': len(unique_floats),
            'years': sorted(list(unique_years)),
            'datasets': sorted(list(datasets_used)),
            'lat_range': {'min': min(lats), 'max': max(lats)},
            'lon_range': {'min': min(lons), 'max': max(lons)},
            'depth_range': {'min': min(depths), 'max': max(depths)},
            'avg_depth': sum(depths) / len(depths),
            'temp_range': {'min': min(temps), 'max': max(temps)} if temps else None,
            'sal_range': {'min': min(sals), 'max': max(sals)} if sals else None,
            'avg_temp': sum(temps) / len(temps) if temps else None,
            'avg_sal': sum(sals) / len(sals) if sals else None,
            'qc_summary': {
                'good': good_count,
                'flagged': flagged_count,
                'good_percent': round(100 * good_count / len(qc_flags), 1) if qc_flags else 0,
            },
        }
    else:
        stats = {
            'total_profiles': 0,
            'returned_profiles': 0,
            'unique_floats': 0,
            'years': [],
            'datasets': [],
        }
    
    return {
        'profiles': enriched_profiles,
        'stats': stats,
        'region_detected': region_detected,
        'count': len(enriched_profiles),
        'total': total_count,
        'has_more': total_count > offset + limit,
        'available_years': get_available_years(),
    }


def get_region_bbox(region: str) -> tuple:
    """
    Get bounding box for named regions.
    
    Returns:
        Tuple of (bbox, region_name) where bbox is [lon_min, lat_min, lon_max, lat_max]
    """
    regions = {
        'arabian sea': ([50.0, 5.0, 77.0, 28.0], 'Arabian Sea'),
        'arabian': ([50.0, 5.0, 77.0, 28.0], 'Arabian Sea'),
        'bay of bengal': ([77.0, 5.0, 100.0, 25.0], 'Bay of Bengal'),
        'bengal': ([77.0, 5.0, 100.0, 25.0], 'Bay of Bengal'),
        'indian ocean': ([20.0, -70.0, 145.0, 30.0], 'Indian Ocean'),
        'indian': ([20.0, -70.0, 145.0, 30.0], 'Indian Ocean'),
        'southern ocean': ([20.0, -70.0, 145.0, -40.0], 'Southern Ocean'),
        'southern': ([20.0, -70.0, 145.0, -40.0], 'Southern Ocean'),
        'red sea': ([32.0, 12.0, 44.0, 30.0], 'Red Sea'),
        'persian gulf': ([47.0, 23.0, 57.0, 32.0], 'Persian Gulf'),
        'gulf': ([47.0, 23.0, 57.0, 32.0], 'Persian Gulf'),
        'madagascar': ([42.0, -28.0, 52.0, -11.0], 'Madagascar'),
        'mozambique': ([30.0, -28.0, 45.0, -10.0], 'Mozambique Channel'),
        'equatorial': ([40.0, -10.0, 100.0, 10.0], 'Equatorial Indian Ocean'),
        'south indian': ([20.0, -50.0, 120.0, -10.0], 'South Indian Ocean'),
        'north indian': ([40.0, 0.0, 100.0, 30.0], 'North Indian Ocean'),
        'australia': ([110.0, -45.0, 155.0, -10.0], 'Australian Waters'),
        'pacific': ([-180.0, -60.0, 180.0, 60.0], 'Pacific Ocean'),
        'atlantic': ([-80.0, -60.0, 0.0, 60.0], 'Atlantic Ocean'),
    }
    
    for key, (bbox, name) in regions.items():
        if key in region.lower():
            return bbox, name
    
    # Default to full Indian Ocean
    return [20.0, -70.0, 145.0, 30.0], 'Indian Ocean'


def load_netcdf_profile(file_path: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Load detailed profile data from a NetCDF file.
    
    Args:
        file_path: Path to the NetCDF file (can be relative or just filename)
        year: Optional year to help locate the file
        
    Returns:
        Dict with full profile data including depth profiles
    """
    try:
        import netCDF4 as nc
    except ImportError:
        logger.error("netCDF4 not installed. Run: pip install netCDF4")
        return None
    
    datasets = scan_datasets()
    nc_path = None
    
    # Find the file
    if os.path.isabs(file_path) and Path(file_path).exists():
        nc_path = Path(file_path)
    else:
        filename = os.path.basename(file_path)
        
        # Search in specific year first if provided
        if year and str(year) in datasets:
            netcdf_dir = datasets[str(year)]["netcdf_dir"]
            candidate = netcdf_dir / filename
            if candidate.exists():
                nc_path = candidate
            else:
                # Try with wildcards
                for f in netcdf_dir.glob(f"*{filename}"):
                    nc_path = f
                    break
        
        # Search all datasets if not found
        if not nc_path:
            for dataset_info in datasets.values():
                netcdf_dir = dataset_info["netcdf_dir"]
                candidate = netcdf_dir / filename
                if candidate.exists():
                    nc_path = candidate
                    break
                # Try with wildcards
                for f in netcdf_dir.glob(f"*{filename}"):
                    nc_path = f
                    break
                if nc_path:
                    break
    
    if not nc_path or not nc_path.exists():
        logger.warning(f"NetCDF file not found: {file_path}")
        return None
    
    try:
        ds = nc.Dataset(str(nc_path))
        
        # Extract basic info
        platform_number = ds.variables['platform_number'][:].tobytes().decode().strip()
        latitude = float(ds.variables['latitude'][0])
        longitude = float(ds.variables['longitude'][0])
        cycle_number = int(ds.variables['cycle_number'][0])
        data_mode = ds.variables['data_mode'][:].tobytes().decode().strip()
        
        # Extract profile data (use adjusted if available, else raw)
        temp_var = 'temp_adjusted' if 'temp_adjusted' in ds.variables else 'temp'
        psal_var = 'psal_adjusted' if 'psal_adjusted' in ds.variables else 'psal'
        pres_var = 'pres_adjusted' if 'pres_adjusted' in ds.variables else 'pres'
        
        temp = ds.variables[temp_var][0, :].data
        psal = ds.variables[psal_var][0, :].data
        pres = ds.variables[pres_var][0, :].data
        
        # Get QC flags
        temp_qc = ds.variables.get('temp_qc', None)
        if temp_qc:
            temp_qc = temp_qc[0, :].tobytes().decode()
        
        # Handle fill values (typically 99999)
        temp = np.where(temp > 50, np.nan, temp)
        psal = np.where(psal > 50, np.nan, psal)
        pres = np.where(pres > 10000, np.nan, pres)
        
        # Get reference time
        juld = float(ds.variables['juld'][0])
        ref_date = datetime(1950, 1, 1)
        from datetime import timedelta
        profile_date = ref_date + timedelta(days=juld)
        
        ds.close()
        
        return {
            'profile_id': f"{platform_number}_{cycle_number:03d}",
            'float_id': platform_number,
            'cycle_number': cycle_number,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': profile_date.isoformat(),
            'date': profile_date.strftime('%Y-%m-%d'),
            'year': profile_date.year,
            'data_mode': data_mode,
            'temperature_profile': temp[~np.isnan(temp)].tolist(),
            'salinity_profile': psal[~np.isnan(psal)].tolist(),
            'pressure_profile': pres[~np.isnan(pres)].tolist(),
            'temperature': float(np.nanmean(temp[:10])) if len(temp) > 0 else None,
            'salinity': float(np.nanmean(psal[:10])) if len(psal) > 0 else None,
            'depth': float(np.nanmax(pres)) if len(pres) > 0 else None,
            'qc_temp': temp_qc[:5] if temp_qc else None,
            'n_levels': len(temp),
            'source_file': str(nc_path),
        }
        
    except Exception as e:
        logger.error(f"Error loading NetCDF file {nc_path}: {e}")
        return None


def get_float_trajectory(float_id: str, years: Optional[List[int]] = None) -> List[Dict]:
    """
    Get the trajectory (all positions) for a specific float across all years.
    
    Args:
        float_id: The WMO float ID
        years: Optional list of years to search
        
    Returns:
        List of positions sorted by date
    """
    profiles = load_index_files(years=years)
    
    trajectory = [p for p in profiles if p['float_id'] == float_id]
    trajectory.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '')
    
    return trajectory


def compare_regions(region1: str, region2: str, years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Compare ARGO data between two regions.
    
    Args:
        region1: First region name
        region2: Second region name
        years: Optional list of years to include
        
    Returns:
        Dict with comparison data for both regions
    """
    data1 = query_profiles(region=region1, years=years, limit=500)
    data2 = query_profiles(region=region2, years=years, limit=500)
    
    return {
        'region1': {
            'name': data1['region_detected'],
            'profiles': data1['profiles'][:50],
            'stats': data1['stats'],
        },
        'region2': {
            'name': data2['region_detected'],
            'profiles': data2['profiles'][:50],
            'stats': data2['stats'],
        },
        'comparison': {
            'profile_count_diff': data1['stats']['total_profiles'] - data2['stats']['total_profiles'],
            'float_count_diff': data1['stats']['unique_floats'] - data2['stats']['unique_floats'],
        },
        'years_included': get_available_years() if not years else years,
    }


def compare_years(year1: int, year2: int, region: Optional[str] = None) -> Dict[str, Any]:
    """
    Compare ARGO data between two years.
    
    Args:
        year1: First year
        year2: Second year
        region: Optional region to filter
        
    Returns:
        Dict with comparison data for both years
    """
    data1 = query_profiles(region=region, years=[year1], limit=500)
    data2 = query_profiles(region=region, years=[year2], limit=500)
    
    return {
        'year1': {
            'year': year1,
            'region': data1['region_detected'],
            'profiles': data1['profiles'][:50],
            'stats': data1['stats'],
        },
        'year2': {
            'year': year2,
            'region': data2['region_detected'],
            'profiles': data2['profiles'][:50],
            'stats': data2['stats'],
        },
        'comparison': {
            'profile_count_diff': data1['stats']['total_profiles'] - data2['stats']['total_profiles'],
            'float_count_diff': data1['stats']['unique_floats'] - data2['stats']['unique_floats'],
        }
    }


def get_yearly_stats(region: Optional[str] = None) -> List[Dict]:
    """
    Get statistics for each year in the dataset.
    
    Args:
        region: Optional region to filter
        
    Returns:
        List of yearly statistics
    """
    stats = []
    
    for year in get_available_years():
        data = query_profiles(region=region, years=[year], limit=1)
        all_profiles = load_index_files(years=[year])
        
        if region:
            bbox, _ = get_region_bbox(region)
            all_profiles = [
                p for p in all_profiles
                if bbox[0] <= p['longitude'] <= bbox[2] and bbox[1] <= p['latitude'] <= bbox[3]
            ]
        
        unique_floats = set(p['float_id'] for p in all_profiles)
        
        stats.append({
            'year': year,
            'dataset': f"argo_data_{year}",
            'profile_count': len(all_profiles),
            'unique_floats': len(unique_floats),
            'region': data.get('region_detected'),
        })
    
    return stats


def get_monthly_stats(year: Optional[int] = None, region: Optional[str] = None) -> List[Dict]:
    """
    Get statistics for each month in the dataset.
    
    Args:
        year: Optional specific year (if None, uses all years)
        region: Optional region to filter
        
    Returns:
        List of monthly statistics
    """
    stats = []
    years = [year] if year else get_available_years()
    
    for y in years:
        for month in range(1, 13):
            profiles = load_index_files(months=[month], years=[y])
            
            if region:
                bbox, _ = get_region_bbox(region)
                profiles = [
                    p for p in profiles
                    if bbox[0] <= p['longitude'] <= bbox[2] and bbox[1] <= p['latitude'] <= bbox[3]
                ]
            
            if profiles:
                unique_floats = set(p['float_id'] for p in profiles)
                
                stats.append({
                    'year': y,
                    'month': month,
                    'month_name': datetime(y, month, 1).strftime('%B'),
                    'profile_count': len(profiles),
                    'unique_floats': len(unique_floats),
                })
    
    return stats


def detect_query_intent(query: str) -> Dict[str, Any]:
    """
    Parse a natural language query to extract search parameters.
    
    Args:
        query: Natural language query
        
    Returns:
        Dict with extracted parameters
    """
    query_lower = query.lower()
    
    # Detect region
    region = None
    for region_name in ['arabian sea', 'bay of bengal', 'indian ocean', 'southern ocean',
                        'red sea', 'persian gulf', 'madagascar', 'mozambique', 'australia',
                        'equatorial', 'north indian', 'south indian', 'pacific', 'atlantic']:
        if region_name in query_lower:
            region = region_name
            break
    
    # Detect years (e.g., "2019", "2020", "2019-2021")
    import re
    years = None
    year_matches = re.findall(r'\b(20\d{2})\b', query)
    if year_matches:
        years = [int(y) for y in year_matches]
    
    # Detect year range (e.g., "2019 to 2021", "2019-2021")
    range_match = re.search(r'(20\d{2})\s*(?:to|-)\s*(20\d{2})', query_lower)
    if range_match:
        start_year = int(range_match.group(1))
        end_year = int(range_match.group(2))
        years = list(range(start_year, end_year + 1))
    
    # Detect month
    months = None
    month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                   'july', 'august', 'september', 'october', 'november', 'december']
    for i, name in enumerate(month_names, 1):
        if name in query_lower:
            months = [i]
            break
    
    # Detect float ID (7-digit number)
    float_match = re.search(r'\b(\d{7})\b', query)
    float_ids = [float_match.group(1)] if float_match else None
    
    # Detect depth
    depth_match = re.search(r'(\d+)\s*(?:m|meters?|depth)', query_lower)
    depth_max = int(depth_match.group(1)) if depth_match else None
    
    # Detect limit
    limit_match = re.search(r'(?:top|first|show)\s*(\d+)', query_lower)
    limit = int(limit_match.group(1)) if limit_match else 100
    
    # Detect comparison
    is_compare = any(word in query_lower for word in ['compare', 'versus', 'vs', 'difference'])
    is_year_compare = is_compare and len(years or []) >= 2
    
    return {
        'region': region,
        'months': months,
        'years': years,
        'float_ids': float_ids,
        'depth_max': depth_max,
        'limit': min(limit, 500),
        'is_compare': is_compare,
        'is_year_compare': is_year_compare,
    }


def query_from_text(query: str) -> Dict[str, Any]:
    """
    Execute a query from natural language text.
    
    Args:
        query: Natural language query
        
    Returns:
        Query results with profiles and stats
    """
    params = detect_query_intent(query)
    
    # Year comparison
    if params['is_year_compare'] and params['years'] and len(params['years']) >= 2:
        return compare_years(params['years'][0], params['years'][1], params['region'])
    
    # Region comparison
    if params['is_compare']:
        query_lower = query.lower()
        regions = []
        for region_name in ['arabian sea', 'bay of bengal', 'indian ocean', 'southern ocean']:
            if region_name in query_lower:
                regions.append(region_name)
        
        if len(regions) >= 2:
            return compare_regions(regions[0], regions[1], params['years'])
    
    result = query_profiles(
        region=params['region'],
        float_ids=params['float_ids'],
        months=params['months'],
        years=params['years'],
        depth_max=params['depth_max'],
        limit=params['limit'],
    )
    
    return result


def refresh_cache():
    """Force refresh of dataset cache."""
    global _datasets_cache, _all_profiles_cache, _last_scan_time
    _datasets_cache = {}
    _all_profiles_cache = None
    _last_scan_time = None
    return scan_datasets()


# Initialize on import
def _init():
    """Initialize the data loader."""
    datasets = scan_datasets()
    if datasets:
        years = get_available_years()
        logger.info(f"ARGO data loader initialized with {len(datasets)} datasets: {years}")
    else:
        logger.warning(f"No ARGO datasets found in {DATA_ROOT}")
        logger.info("Add datasets as folders named 'argo_data_YYYY' (e.g., argo_data_2019)")


_init()
