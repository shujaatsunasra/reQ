"""
Visualization Suggestion Engine

Analyzes query context and data to suggest appropriate visualizations.
"""

from typing import List, Dict, Any, Optional
import re

from core.logging import get_logger

logger = get_logger(__name__)


# Visualization types and their trigger patterns
VISUALIZATION_TRIGGERS = {
    "trajectory_map": {
        "keywords": ["trajectory", "path", "track", "float", "journey", "movement", "where", "location"],
        "data_requirements": ["latitude", "longitude", "float_id"],
        "description": "Animated map showing float movement over time",
        "library": "leaflet",
        "priority": 1,  # Primary visualization for spatial data
    },
    "time_series": {
        "keywords": ["trend", "over time", "history", "change", "evolution", "time series", "yearly", "monthly"],
        "data_requirements": ["timestamp"],
        "description": "Line chart showing parameter changes over time",
        "library": "recharts",
        "priority": 2,
    },
    "vertical_profile": {
        "keywords": ["profile", "vertical", "depth", "structure", "layer", "stratification"],
        "data_requirements": ["depth", "temperature"],
        "description": "Depth vs parameter chart showing vertical ocean structure",
        "library": "plotly",
        "priority": 2,
    },
    "ts_diagram": {
        "keywords": ["t-s", "water mass", "mixing", "characteristics", "t-s diagram"],
        "data_requirements": ["temperature", "salinity"],
        "description": "Temperature-Salinity diagram for water mass identification",
        "library": "plotly",
        "priority": 3,
    },
    "hovmoller": {
        "keywords": ["hovmoller", "depth-time", "evolution", "temporal", "seasonal depth"],
        "data_requirements": ["depth", "timestamp", "temperature"],
        "description": "Depth-time contour showing temporal evolution by depth",
        "library": "plotly",
        "priority": 3,
    },
    "heatmap": {
        "keywords": ["distribution", "spatial", "heatmap", "map", "region", "area"],
        "data_requirements": ["latitude", "longitude", "temperature"],
        "description": "Geospatial heatmap of parameter distribution",
        "library": "plotly",
        "priority": 2,
    },
    "qc_dashboard": {
        "keywords": ["quality", "qc", "flag", "data quality", "validation"],
        "data_requirements": ["qc_flag"],
        "description": "Quality control flag distribution dashboard",
        "library": "recharts",
        "priority": 4,
    },
}


def suggest_visualizations(
    query: str,
    data: Optional[Dict[str, Any]] = None,
    max_suggestions: int = 3
) -> List[Dict[str, Any]]:
    """
    Suggest appropriate visualizations based on query and data.
    
    Args:
        query: The user's natural language query
        data: Optional data context with available fields
        max_suggestions: Maximum number of suggestions to return
        
    Returns:
        List of visualization suggestions with type, description, and reason
    """
    query_lower = query.lower()
    suggestions = []
    
    # Score each visualization type
    for viz_type, config in VISUALIZATION_TRIGGERS.items():
        score = 0
        reasons = []
        
        # Check keyword matches
        for keyword in config["keywords"]:
            if keyword in query_lower:
                score += 10
                reasons.append(f"matches '{keyword}'")
        
        # Check data availability if data provided
        if data:
            profiles = data.get("profiles", [])
            if profiles:
                available_fields = set()
                for profile in profiles[:5]:  # Sample first 5
                    available_fields.update(profile.keys())
                
                # Check if required data fields are available
                required_fields = set(config["data_requirements"])
                field_matches = required_fields & available_fields
                
                if len(field_matches) == len(required_fields):
                    score += 20
                    reasons.append("data requirements met")
                elif field_matches:
                    score += 10
                    reasons.append(f"partial data ({len(field_matches)}/{len(required_fields)} fields)")
        
        # Add to suggestions if score > 0
        if score > 0:
            suggestions.append({
                "type": viz_type,
                "score": score,
                "priority": config["priority"],
                "description": config["description"],
                "library": config["library"],
                "reason": ", ".join(reasons) if reasons else "general match",
            })
    
    # Sort by score (descending) then priority (ascending)
    suggestions.sort(key=lambda x: (-x["score"], x["priority"]))
    
    # If no suggestions based on query, suggest based on data
    if not suggestions and data:
        profiles = data.get("profiles", [])
        if profiles:
            # Default suggestions based on available data
            sample = profiles[0] if profiles else {}
            
            if "latitude" in sample and "longitude" in sample:
                suggestions.append({
                    "type": "trajectory_map",
                    "score": 15,
                    "priority": 1,
                    "description": "Animated map showing float positions",
                    "library": "leaflet",
                    "reason": "spatial data available",
                })
            
            if "temperature" in sample:
                suggestions.append({
                    "type": "time_series",
                    "score": 10,
                    "priority": 2,
                    "description": "Temperature trends over time",
                    "library": "recharts",
                    "reason": "temperature data available",
                })
    
    # Take top N suggestions
    result = suggestions[:max_suggestions]
    
    # Add explanation for primary suggestion
    if result:
        result[0]["is_primary"] = True
        result[0]["explanation"] = _generate_explanation(result[0], query)
    
    return result


def _generate_explanation(suggestion: Dict[str, Any], query: str) -> str:
    """Generate a human-readable explanation for why this visualization was chosen."""
    viz_type = suggestion["type"]
    reason = suggestion.get("reason", "")
    
    explanations = {
        "trajectory_map": f"I recommend a trajectory map because your query involves tracking float positions in the ocean.",
        "time_series": f"A time series chart will help you see how values change over time.",
        "vertical_profile": f"A vertical profile chart shows how temperature/salinity varies with depth.",
        "ts_diagram": f"A T-S diagram helps identify water masses based on their temperature-salinity characteristics.",
        "hovmoller": f"A Hovmöller diagram shows how conditions change with both depth and time.",
        "heatmap": f"A heatmap provides a clear view of the spatial distribution of your parameter.",
        "qc_dashboard": f"A QC dashboard helps you understand the quality of your data.",
    }
    
    return explanations.get(viz_type, f"This visualization type best matches your query.")


def get_deep_research_config_from_query(query: str) -> Dict[str, Any]:
    """
    Extract research configuration from a natural language query.
    
    Identifies focus area, region, time range, and parameters.
    """
    query_lower = query.lower()
    config = {}
    
    # Detect focus
    if any(word in query_lower for word in ["seasonal", "monsoon", "winter", "summer"]):
        config["focus"] = "seasonal"
    elif any(word in query_lower for word in ["trend", "long-term", "change over", "years"]):
        config["focus"] = "trends"
    elif any(word in query_lower for word in ["anomaly", "unusual", "strange", "deviation"]):
        config["focus"] = "anomalies"
    elif any(word in query_lower for word in ["water mass", "mixing", "t-s"]):
        config["focus"] = "water_mass"
    
    # Detect region
    region_map = {
        "arabian sea": {"name": "Arabian Sea", "bbox": [50, 5, 77, 28]},
        "bay of bengal": {"name": "Bay of Bengal", "bbox": [77, 5, 100, 25]},
        "indian ocean": {"name": "Indian Ocean", "bbox": [20, -70, 145, 30]},
        "southern ocean": {"name": "Southern Ocean", "bbox": [20, -70, 145, -40]},
    }
    
    for region_key, region_data in region_map.items():
        if region_key in query_lower:
            config["region"] = region_data
            break
    
    # Detect parameters
    parameters = []
    if "temperature" in query_lower or "temp" in query_lower:
        parameters.append("temperature")
    if "salinity" in query_lower or "salt" in query_lower:
        parameters.append("salinity")
    
    if parameters:
        config["parameters"] = parameters
    else:
        config["parameters"] = ["temperature"]  # Default
    
    # Detect time range
    year_match = re.findall(r'20\d{2}', query)
    if year_match:
        config["years"] = [int(y) for y in year_match]
    
    return config
