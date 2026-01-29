"""
Demo Data Module - Provides realistic mock ARGO data for development/demo.
Used when database is not connected or DEMO_MODE is enabled.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import math

# Realistic ARGO float positions in major ocean basins
DEMO_REGIONS = {
    "arabian_sea": {
        "bounds": {"min_lat": 5, "max_lat": 25, "min_lon": 50, "max_lon": 78},
        "float_prefix": "29",
        "avg_temp": 27.5,
        "avg_salinity": 36.2,
    },
    "bay_of_bengal": {
        "bounds": {"min_lat": 5, "max_lat": 23, "min_lon": 80, "max_lon": 95},
        "float_prefix": "29",
        "avg_temp": 28.0,
        "avg_salinity": 33.5,
    },
    "mediterranean": {
        "bounds": {"min_lat": 30, "max_lat": 46, "min_lon": -6, "max_lon": 36},
        "float_prefix": "69",
        "avg_temp": 18.5,
        "avg_salinity": 38.5,
    },
    "pacific_equatorial": {
        "bounds": {"min_lat": -10, "max_lat": 10, "min_lon": -180, "max_lon": -100},
        "float_prefix": "59",
        "avg_temp": 26.0,
        "avg_salinity": 35.0,
    },
    "atlantic_north": {
        "bounds": {"min_lat": 30, "max_lat": 60, "min_lon": -80, "max_lon": -10},
        "float_prefix": "49",
        "avg_temp": 15.0,
        "avg_salinity": 35.5,
    },
    "indian_ocean": {
        "bounds": {"min_lat": -40, "max_lat": 10, "min_lon": 40, "max_lon": 110},
        "float_prefix": "19",
        "avg_temp": 24.0,
        "avg_salinity": 35.0,
    },
    "southern_ocean": {
        "bounds": {"min_lat": -70, "max_lat": -40, "min_lon": -180, "max_lon": 180},
        "float_prefix": "79",
        "avg_temp": 2.0,
        "avg_salinity": 34.5,
    },
}


def generate_float_id(region_key: str = None) -> str:
    """Generate a realistic ARGO float WMO ID."""
    if region_key and region_key in DEMO_REGIONS:
        prefix = DEMO_REGIONS[region_key]["float_prefix"]
    else:
        prefix = random.choice(["19", "29", "39", "49", "59", "69"])
    return f"{prefix}{random.randint(10000, 99999)}"


def generate_profile(
    float_id: str,
    region_key: str,
    cycle: int,
    base_date: datetime
) -> Dict[str, Any]:
    """Generate a single ARGO profile with realistic data."""
    region = DEMO_REGIONS[region_key]
    bounds = region["bounds"]
    
    # Random position within region
    lat = random.uniform(bounds["min_lat"], bounds["max_lat"])
    lon = random.uniform(bounds["min_lon"], bounds["max_lon"])
    
    # Timestamp with some variation
    timestamp = base_date + timedelta(days=cycle * 10 + random.randint(-2, 2))
    
    # Temperature and salinity with realistic variation
    temp = region["avg_temp"] + random.gauss(0, 2)
    salinity = region["avg_salinity"] + random.gauss(0, 0.5)
    
    # Occasionally generate anomalous data (10% chance)
    is_anomaly = random.random() < 0.10
    anomaly_type = None
    anomaly_score = 0.0
    
    if is_anomaly:
        anomaly_type = random.choice(["temperature", "salinity", "both"])
        if anomaly_type in ["temperature", "both"]:
            # Significant temperature anomaly (±5-10°C from average)
            temp_deviation = random.choice([-1, 1]) * random.uniform(5, 10)
            temp = region["avg_temp"] + temp_deviation
            anomaly_score = min(1.0, abs(temp_deviation) / 10)
        if anomaly_type in ["salinity", "both"]:
            # Significant salinity anomaly (±2-4 PSU from average)
            sal_deviation = random.choice([-1, 1]) * random.uniform(2, 4)
            salinity = region["avg_salinity"] + sal_deviation
            anomaly_score = max(anomaly_score, min(1.0, abs(sal_deviation) / 4))
    
    # Depth (surface measurement)
    depth = random.uniform(5, 50)
    
    # QC flags (mostly good data, but anomalies more likely to have issues)
    if is_anomaly:
        qc_flag = random.choices([1, 2, 3, 4], weights=[40, 30, 20, 10])[0]
    else:
        qc_flag = random.choices([1, 2, 3, 4], weights=[85, 10, 3, 2])[0]
    
    # Data mode
    data_mode = random.choices(["R", "A", "D"], weights=[40, 40, 20])[0]
    
    return {
        "profile_id": f"{float_id}_{cycle:03d}",
        "float_id": float_id,
        "cycle_number": cycle,
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "timestamp": timestamp.isoformat(),
        "date": timestamp.strftime("%Y-%m-%d"),
        "temperature": round(temp, 2),
        "salinity": round(salinity, 2),
        "depth": round(depth, 1),
        "qc_flag": qc_flag,
        "qc_temp": str(qc_flag),
        "data_mode": data_mode,
        "direction": "A",
        "is_anomaly": is_anomaly,
        "anomaly_type": anomaly_type,
        "anomaly_score": round(anomaly_score, 3),
    }


def generate_demo_float_data(
    region: str = None,
    count: int = 50,
    start_date: datetime = None
) -> List[Dict[str, Any]]:
    """
    Generate demo float profiles for a region.
    
    Args:
        region: Region key (e.g., 'arabian_sea', 'mediterranean')
        count: Number of profiles to generate
        start_date: Starting date for data generation
    
    Returns:
        List of profile dictionaries
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=365)
    
    profiles = []
    
    # Determine which regions to use
    if region:
        # Try to match region name
        region_key = None
        region_lower = region.lower().replace(" ", "_")
        for key in DEMO_REGIONS:
            if key in region_lower or region_lower in key:
                region_key = key
                break
        
        if not region_key:
            # Default to random regions
            region_keys = list(DEMO_REGIONS.keys())
        else:
            region_keys = [region_key]
    else:
        region_keys = list(DEMO_REGIONS.keys())
    
    # Generate floats across regions
    floats_per_region = max(1, count // len(region_keys) // 5)  # 5 profiles per float
    
    for region_key in region_keys:
        for _ in range(floats_per_region):
            float_id = generate_float_id(region_key)
            num_cycles = random.randint(3, 8)
            
            for cycle in range(1, num_cycles + 1):
                profile = generate_profile(float_id, region_key, cycle, start_date)
                profiles.append(profile)
                
                if len(profiles) >= count:
                    return profiles
    
    return profiles[:count]


def query_demo_data(
    query: str,
    filters: Dict[str, Any] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Query demo data based on natural language query hints.
    
    Args:
        query: The user's query (used to detect region/parameters)
        filters: Additional filter constraints
        limit: Maximum results to return
    
    Returns:
        Dict with profiles, count, and stats
    """
    query_lower = query.lower()
    
    # Detect region from query
    region = None
    for region_name in ["arabian sea", "bay of bengal", "mediterranean", 
                        "pacific", "atlantic", "indian ocean", "southern ocean"]:
        if region_name in query_lower:
            region = region_name
            break
    
    # Adjust count based on query hints
    if "recent" in query_lower or "latest" in query_lower:
        count = min(100, limit)
        start_date = datetime.now() - timedelta(days=30)
    elif "all" in query_lower or "many" in query_lower:
        count = min(500, limit)
        start_date = datetime.now() - timedelta(days=365)
    else:
        count = min(200, limit)
        start_date = datetime.now() - timedelta(days=180)
    
    # Generate profiles
    profiles = generate_demo_float_data(region=region, count=count, start_date=start_date)
    
    # Apply filters if provided
    if filters:
        if filters.get("qcFlags"):
            profiles = [p for p in profiles if p.get("qc_flag") in filters["qcFlags"]]
        
        if filters.get("dataMode"):
            profiles = [p for p in profiles if p.get("data_mode") in filters["dataMode"]]
        
        if filters.get("tempRange"):
            min_t, max_t = filters["tempRange"].get("min", -5), filters["tempRange"].get("max", 40)
            profiles = [p for p in profiles if min_t <= p.get("temperature", 0) <= max_t]
        
        if filters.get("bbox"):
            bbox = filters["bbox"]
            profiles = [
                p for p in profiles 
                if (bbox.get("minLat", -90) <= p.get("latitude", 0) <= bbox.get("maxLat", 90)
                    and bbox.get("minLng", -180) <= p.get("longitude", 0) <= bbox.get("maxLng", 180))
            ]
    
    # Calculate stats
    if profiles:
        temps = [p["temperature"] for p in profiles if p.get("temperature")]
        sals = [p["salinity"] for p in profiles if p.get("salinity")]
        depths = [p["depth"] for p in profiles if p.get("depth")]
        anomalies = [p for p in profiles if p.get("is_anomaly")]
        
        stats = {
            "avg_temp": round(sum(temps) / len(temps), 2) if temps else None,
            "avg_salinity": round(sum(sals) / len(sals), 2) if sals else None,
            "temp_range": {"min": round(min(temps), 1), "max": round(max(temps), 1)} if temps else None,
            "depth_range": {"min": round(min(depths), 1), "max": round(max(depths), 1)} if depths else None,
            "unique_floats": len(set(p["float_id"] for p in profiles)),
            "qc_distribution": {
                "good": len([p for p in profiles if p.get("qc_flag") == 1]),
                "probably_good": len([p for p in profiles if p.get("qc_flag") == 2]),
                "probably_bad": len([p for p in profiles if p.get("qc_flag") == 3]),
                "bad": len([p for p in profiles if p.get("qc_flag") == 4]),
            },
            "anomalies": {
                "count": len(anomalies),
                "percentage": round(len(anomalies) / len(profiles) * 100, 1) if profiles else 0,
                "by_type": {
                    "temperature": len([a for a in anomalies if a.get("anomaly_type") == "temperature"]),
                    "salinity": len([a for a in anomalies if a.get("anomaly_type") == "salinity"]),
                    "both": len([a for a in anomalies if a.get("anomaly_type") == "both"]),
                },
                "avg_score": round(sum(a.get("anomaly_score", 0) for a in anomalies) / len(anomalies), 2) if anomalies else 0,
            }
        }
    else:
        stats = {}
    
    return {
        "profiles": profiles,
        "count": len(profiles),
        "stats": stats,
        "demo_mode": True,
        "region_detected": region,
    }


def get_demo_float_details(float_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed info for a specific demo float."""
    # Generate consistent data for the float ID
    random.seed(hash(float_id) % 2**32)
    
    region_key = random.choice(list(DEMO_REGIONS.keys()))
    profiles = []
    
    base_date = datetime.now() - timedelta(days=365)
    num_cycles = random.randint(5, 15)
    
    for cycle in range(1, num_cycles + 1):
        profile = generate_profile(float_id, region_key, cycle, base_date)
        profiles.append(profile)
    
    # Reset random state
    random.seed()
    
    return {
        "float_id": float_id,
        "wmo_id": float_id,
        "dac": "demo",
        "institution": "Demo Institution",
        "project_name": "ARGO Demo",
        "total_cycles": len(profiles),
        "first_date": profiles[0]["date"] if profiles else None,
        "last_date": profiles[-1]["date"] if profiles else None,
        "profiles": profiles,
        "demo_mode": True,
    }


def compare_demo_data(
    query: str,
    region1: str = None,
    region2: str = None
) -> Dict[str, Any]:
    """Generate comparison data between two regions/datasets."""
    # Extract regions from query if not provided
    query_lower = query.lower()
    
    regions_found = []
    for region_name in DEMO_REGIONS.keys():
        readable_name = region_name.replace("_", " ")
        if readable_name in query_lower:
            regions_found.append(region_name)
    
    if len(regions_found) >= 2:
        region1, region2 = regions_found[0], regions_found[1]
    elif len(regions_found) == 1:
        region1 = regions_found[0]
        region2 = random.choice([k for k in DEMO_REGIONS.keys() if k != region1])
    else:
        region1, region2 = random.sample(list(DEMO_REGIONS.keys()), 2)
    
    data1 = query_demo_data(region1.replace("_", " "), limit=30)
    data2 = query_demo_data(region2.replace("_", " "), limit=30)
    
    return {
        "comparison": {
            "region1": {
                "name": region1.replace("_", " ").title(),
                "profiles": data1["profiles"],
                "stats": data1["stats"],
            },
            "region2": {
                "name": region2.replace("_", " ").title(),
                "profiles": data2["profiles"],
                "stats": data2["stats"],
            },
        },
        "differences": {
            "temp_diff": round(
                (data1["stats"].get("avg_temp", 0) or 0) - 
                (data2["stats"].get("avg_temp", 0) or 0), 
                2
            ),
            "salinity_diff": round(
                (data1["stats"].get("avg_salinity", 0) or 0) - 
                (data2["stats"].get("avg_salinity", 0) or 0),
                2
            ),
        },
        "demo_mode": True,
    }
