"""
Domain knowledge for oceanographic data.
Contains mappings for regions, parameters, and other domain-specific data.
"""

# Ocean regions with bounding boxes [min_lon, min_lat, max_lon, max_lat]
OCEAN_REGIONS = {
    "Arabian Sea": {
        "bbox": [50, 8, 77, 28],
        "center": [63.5, 18]
    },
    "Bay of Bengal": {
        "bbox": [80, 5, 95, 23],
        "center": [87.5, 14]
    },
    "North Atlantic": {
        "bbox": [-80, 20, 0, 65],
        "center": [-40, 42.5]
    },
    "South Atlantic": {
        "bbox": [-70, -60, 20, 0],
        "center": [-25, -30]
    },
    "North Pacific": {
        "bbox": [100, 0, -100, 65],
        "center": [180, 32.5]
    },
    "South Pacific": {
        "bbox": [140, -60, -70, 0],
        "center": [-145, -30]
    },
    "Indian Ocean": {
        "bbox": [20, -60, 120, 30],
        "center": [70, -15]
    },
    "Southern Ocean": {
        "bbox": [-180, -90, 180, -60],
        "center": [0, -75]
    },
    "Arctic Ocean": {
        "bbox": [-180, 66, 180, 90],
        "center": [0, 78]
    },
    "Mediterranean Sea": {
        "bbox": [-6, 30, 36, 46],
        "center": [15, 38]
    },
    "Gulf of Mexico": {
        "bbox": [-98, 18, -80, 31],
        "center": [-89, 24.5]
    },
    "Caribbean Sea": {
        "bbox": [-88, 9, -60, 22],
        "center": [-74, 15.5]
    },
    "Red Sea": {
        "bbox": [32, 12, 44, 30],
        "center": [38, 21]
    },
    "Persian Gulf": {
        "bbox": [48, 24, 56, 30],
        "center": [52, 27]
    },
    "South China Sea": {
        "bbox": [100, 0, 121, 25],
        "center": [110.5, 12.5]
    },
    "East China Sea": {
        "bbox": [117, 23, 131, 33],
        "center": [124, 28]
    },
    "Sea of Japan": {
        "bbox": [127, 33, 142, 52],
        "center": [134.5, 42.5]
    },
    "Coral Sea": {
        "bbox": [142, -25, 175, -10],
        "center": [158.5, -17.5]
    },
    "Tasman Sea": {
        "bbox": [145, -45, 175, -28],
        "center": [160, -36.5]
    },
    "Weddell Sea": {
        "bbox": [-60, -80, -20, -60],
        "center": [-40, -70]
    },
    "Ross Sea": {
        "bbox": [160, -85, -150, -70],
        "center": [175, -77.5]
    }
}

# Oceanographic parameters mapping
OCEANOGRAPHIC_PARAMETERS = {
    "temperature": {
        "column": "temperature",
        "unit": "°C",
        "aliases": ["temp", "sea temperature", "water temperature", "sst"]
    },
    "salinity": {
        "column": "salinity",
        "unit": "PSU",
        "aliases": ["salt", "psal", "practical salinity"]
    },
    "pressure": {
        "column": "pressure",
        "unit": "dbar",
        "aliases": ["pres", "depth"]
    },
    "oxygen": {
        "column": "doxy",
        "unit": "μmol/kg",
        "aliases": ["dissolved oxygen", "do", "o2"]
    },
    "chlorophyll": {
        "column": "chla",
        "unit": "mg/m³",
        "aliases": ["chl", "chlorophyll-a", "chla"]
    },
    "nitrate": {
        "column": "nitrate",
        "unit": "μmol/kg",
        "aliases": ["no3", "nitrogen"]
    },
    "pH": {
        "column": "ph_in_situ_total",
        "unit": "",
        "aliases": ["acidity"]
    },
    "turbidity": {
        "column": "turbidity",
        "unit": "NTU",
        "aliases": ["turb"]
    }
}

# Common parameters for quick access
COMMON_PARAMETERS = [
    {"name": "temperature", "column": "temperature", "unit": "°C"},
    {"name": "salinity", "column": "salinity", "unit": "PSU"},
    {"name": "pressure", "column": "pressure", "unit": "dbar"}
]

# Quality control mappings
QC_MAPPINGS = {
    "good quality": {"flags": [1], "data_mode": None},
    "high quality": {"flags": [1], "data_mode": None},
    "quality flag 1": {"flags": [1], "data_mode": None},
    "quality flag a": {"flags": [1], "data_mode": "A"},
    "probably good": {"flags": [1, 2], "data_mode": None},
    "bad quality": {"flags": [4], "data_mode": None},
    "poor quality": {"flags": [3, 4], "data_mode": None},
    "questionable": {"flags": [3], "data_mode": None},
    "missing": {"flags": [9], "data_mode": None},
    "all data": {"flags": [1, 2, 3, 4, 8, 9], "data_mode": None}
}

# Depth extraction patterns
DEPTH_PATTERNS = [
    (r"below\s+(\d+)\s*(?:m|meters?|dbar)?", 
     lambda m: {"min": float(m.group(1)), "max": None}),
    (r"above\s+(\d+)\s*(?:m|meters?|dbar)?", 
     lambda m: {"min": None, "max": float(m.group(1))}),
    (r"between\s+(\d+)\s*(?:m|meters?|dbar)?\s+and\s+(\d+)\s*(?:m|meters?|dbar)?",
     lambda m: {"min": float(m.group(1)), "max": float(m.group(2))}),
    (r"(\d+)\s*-\s*(\d+)\s*(?:m|meters?|dbar)?",
     lambda m: {"min": float(m.group(1)), "max": float(m.group(2))}),
    (r"at\s+(\d+)\s*(?:m|meters?|dbar)?",
     lambda m: {"min": float(m.group(1)) - 10, "max": float(m.group(1)) + 10}),
    (r"surface",
     lambda m: {"min": 0, "max": 50}),
    (r"deep",
     lambda m: {"min": 500, "max": None}),
    (r"mixed layer",
     lambda m: {"min": 0, "max": 200}),
    (r"thermocline",
     lambda m: {"min": 50, "max": 500}),
]

# Intent patterns for query classification
OCEANOGRAPHIC_INTENTS = {
    "trajectory_tracking": [
        "trajectory", "path", "route", "movement", "track", "traveled"
    ],
    "profile_analysis": [
        "profile", "vertical", "depth", "column", "section"
    ],
    "time_series_analysis": [
        "time series", "evolution", "change over time", "trend", "seasonal"
    ],
    "spatial_analysis": [
        "distribution", "spatial", "map", "area", "region"
    ],
    "anomaly_detection": [
        "anomaly", "unusual", "abnormal", "outlier", "deviation"
    ],
    "comparison": [
        "compare", "difference", "versus", "vs", "between"
    ],
    "float_tracking": [
        "float", "argo float", "platform"
    ],
    "gradient_analysis": [
        "gradient", "change", "variation", "rate"
    ],
    "water_mass_analysis": [
        "water mass", "t-s", "temperature-salinity", "water type"
    ],
    "mixed_layer_analysis": [
        "mixed layer", "mld", "mixing"
    ],
    "quality_check": [
        "quality", "qc", "flag", "check", "validation"
    ]
}

# Visualization type suggestions based on intent
INTENT_VISUALIZATIONS = {
    "trajectory_tracking": ["trajectory_map"],
    "profile_analysis": ["vertical_profile", "hovmoller"],
    "time_series_analysis": ["time_series", "hovmoller"],
    "spatial_analysis": ["heatmap", "trajectory_map"],
    "anomaly_detection": ["heatmap", "time_series"],
    "comparison": ["vertical_profile", "time_series"],
    "float_tracking": ["trajectory_map", "time_series"],
    "gradient_analysis": ["heatmap", "vertical_profile"],
    "water_mass_analysis": ["ts_diagram"],
    "mixed_layer_analysis": ["hovmoller", "time_series"],
    "quality_check": ["qc_dashboard"],
    "general_query": ["time_series", "vertical_profile"]
}
