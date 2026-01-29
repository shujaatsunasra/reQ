"""Test script to verify real data loading from NetCDF files."""

from core.argo_loader import scan_datasets, query_profiles, find_netcdf_file

print("=== REAL DATA TEST ===")
print()

# Get some profiles - use years and months as lists
result = query_profiles(years=[2019], months=[1], limit=10)
profiles = result.get("profiles", [])

print(f"Loaded {len(profiles)} profiles from query")
print()

# Count data sources
sources = {}
for p in profiles:
    src = p.get("data_source", "unknown")
    sources[src] = sources.get(src, 0) + 1

print(f"Data Sources: {sources}")
print()

# Show sample profiles
for i, p in enumerate(profiles[:5]):
    print(f"--- Profile {i+1}: Float {p.get('float_id')} ---")
    print(f"  Location: {p.get('latitude'):.2f}N, {p.get('longitude'):.2f}E")
    print(f"  Data Source: {p.get('data_source', 'unknown')}")
    if p.get("source_file"):
        import os
        print(f"  Source File: {os.path.basename(p.get('source_file'))}")
    print(f"  Temperature: {p.get('temperature')} C")
    print(f"  Salinity: {p.get('salinity')} PSU")
    print(f"  Depth: {p.get('depth')} m")
    print(f"  QC Flag: {p.get('qc_flag')} (Temp: {p.get('qc_temp')}, Sal: {p.get('qc_psal')})")
    print(f"  Data Mode: {p.get('data_mode')}")
    print(f"  Profile Levels: {p.get('n_levels', 0)}")
    if p.get("temperature_profile"):
        temps = p.get("temperature_profile")[:5]
        print(f"  Temp Profile (first 5): {temps}")
    print()

# Summary
real_count = sources.get("netcdf", 0)
missing_count = sources.get("missing", 0)
print(f"=== SUMMARY ===")
print(f"Real data from NetCDF: {real_count}/{len(profiles)} ({100*real_count/len(profiles) if profiles else 0:.1f}%)")
print(f"Missing/not found: {missing_count}/{len(profiles)}")
