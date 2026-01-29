"""
Explorer Mode - Simplified query endpoint.
Bypasses complex NL2Op/MCP pipeline for direct LLM-powered responses.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time
import uuid
import re

from core.logging import get_logger
from core.llm_service import LLMService
from core.database import get_supabase

logger = get_logger(__name__)
router = APIRouter()


class ExplorerRequest(BaseModel):
    """Request model for explorer queries."""
    query: str = Field(..., description="Natural language query", min_length=1, max_length=2000)
    groq_api_key: Optional[str] = Field(default=None, description="Groq API key")
    huggingface_api_key: Optional[str] = Field(default=None, description="HuggingFace API key")


class ExplorerResponse(BaseModel):
    """Response model for explorer queries."""
    success: bool
    request_id: str
    query: str
    response: str
    data: Optional[Dict[str, Any]] = None
    confidence: float
    execution_time_ms: float
    provider_used: Optional[str] = None
    error: Optional[str] = None
    suggest_power_mode: bool = False  # True when query is too complex for Explorer
    complexity_reason: Optional[str] = None  # Why Power Mode is recommended


# Region mappings for common oceanographic areas
REGION_MAPPINGS = {
    "arabian sea": {"min_lat": 5, "max_lat": 25, "min_lon": 50, "max_lon": 78},
    "bay of bengal": {"min_lat": 5, "max_lat": 23, "min_lon": 80, "max_lon": 95},
    "red sea": {"min_lat": 12, "max_lat": 30, "min_lon": 32, "max_lon": 44},
    "pacific": {"min_lat": -60, "max_lat": 60, "min_lon": -180, "max_lon": -100},
    "atlantic": {"min_lat": -60, "max_lat": 60, "min_lon": -80, "max_lon": 0},
    "indian ocean": {"min_lat": -40, "max_lat": 25, "min_lon": 30, "max_lon": 120},
    "mediterranean": {"min_lat": 30, "max_lat": 46, "min_lon": -6, "max_lon": 36},
    "caribbean": {"min_lat": 9, "max_lat": 25, "min_lon": -90, "max_lon": -60},
    "south china sea": {"min_lat": 0, "max_lat": 25, "min_lon": 100, "max_lon": 125},
    "gulf of mexico": {"min_lat": 18, "max_lat": 31, "min_lon": -98, "max_lon": -80},
    "el nino": {"min_lat": -10, "max_lat": 10, "min_lon": -170, "max_lon": -80},
}


def extract_region(query: str) -> Optional[Dict[str, float]]:
    """Extract region bounds from query text."""
    query_lower = query.lower()
    for region_name, bounds in REGION_MAPPINGS.items():
        if region_name in query_lower:
            return bounds
    return None


def extract_parameter(query: str) -> Optional[str]:
    """Extract oceanographic parameter from query."""
    query_lower = query.lower()
    if "temperature" in query_lower or "temp" in query_lower:
        return "temperature"
    if "salinity" in query_lower:
        return "salinity"
    if "pressure" in query_lower or "depth" in query_lower:
        return "pressure"
    return None


# Keywords indicating complex/advanced queries that need Power Mode
COMPLEX_QUERY_PATTERNS = {
    "analysis": [
        "correlat", "regress", "trend analysis", "time series", "anomaly detect",
        "statistical", "variance", "standard deviation", "clustering", "pattern",
        "machine learning", "predict", "forecast", "model"
    ],
    "comparison": [
        "compare", "versus", "vs", "difference between", "contrast",
        "relative to", "against"
    ],
    "aggregation": [
        "average over", "aggregate", "group by", "histogram", "distribution",
        "percentile", "quartile", "median"
    ],
    "temporal": [
        "seasonal", "monthly trend", "yearly", "interannual", "decadal",
        "climate", "long-term", "historical"
    ],
    "spatial": [
        "cross-section", "transect", "gradient", "interpolat", "grid",
        "contour", "isosurface"
    ],
    "multi_param": [
        "relationship between", "correlation of", "combined", "multi-variable",
        "coupled", "interaction"
    ]
}


def analyze_query_complexity(query: str) -> tuple[bool, Optional[str]]:
    """
    Analyze if query is too complex for Explorer mode.
    
    Returns:
        (is_complex, reason): Tuple of whether query needs Power Mode and why
    """
    query_lower = query.lower()
    
    # Check for complex patterns
    for category, patterns in COMPLEX_QUERY_PATTERNS.items():
        for pattern in patterns:
            if pattern in query_lower:
                reasons = {
                    "analysis": "advanced statistical analysis",
                    "comparison": "comparative data analysis",
                    "aggregation": "complex data aggregation",
                    "temporal": "temporal/seasonal analysis",
                    "spatial": "advanced spatial analysis",
                    "multi_param": "multi-parameter relationships"
                }
                return True, reasons.get(category, "advanced analysis")
    
    # Check for multiple parameters requested
    params_found = 0
    for param in ["temperature", "salinity", "pressure", "density", "oxygen", "chlorophyll"]:
        if param in query_lower:
            params_found += 1
    
    if params_found >= 2:
        return True, "multi-parameter analysis"
    
    # Check for specific depth/pressure ranges (advanced queries)
    if re.search(r'\d+\s*(m|meters?|dbar)\s*(to|-)\s*\d+', query_lower):
        return True, "depth-specific analysis"
    
    # Check for date ranges spanning long periods
    if re.search(r'(from|since|between).*\d{4}.*to.*\d{4}', query_lower):
        return True, "historical time-range analysis"
    
    return False, None


def is_valid_explorer_query(query: str) -> tuple[bool, Optional[str]]:
    """
    Check if query is suitable for Explorer mode (beginner-friendly).
    
    Explorer mode handles:
    - Simple "show me" / "what is" queries
    - Single region lookups
    - Basic counts and listings
    - Recent data exploration
    
    Returns:
        (is_valid, suggestion): Whether query fits Explorer mode and alternate suggestion
    """
    query_lower = query.lower()
    
    # First check complexity
    is_complex, complexity_reason = analyze_query_complexity(query)
    if is_complex:
        return False, complexity_reason
    
    # Valid explorer patterns (beginner-friendly)
    explorer_patterns = [
        r"^(show|list|find|get|display)\s+(me\s+)?(all|the|some|any)?",
        r"^(how many|count|number of)",
        r"^(what|where|which)\s+(is|are|floats?)",
        r"^(latest|recent|newest)",
        r"(in|near|around)\s+(the\s+)?[a-z\s]+$",  # Region queries
        r"^tell me about",
        r"^overview",
        r"^summary"
    ]
    
    # Check if it matches basic explorer patterns
    for pattern in explorer_patterns:
        if re.search(pattern, query_lower):
            return True, None
    
    # Short queries are usually simple enough
    if len(query.split()) <= 8:
        return True, None
    
    return True, None  # Default allow, but might suggest Power Mode later


async def fetch_data_for_query(query: str) -> Dict[str, Any]:
    """
    Fetch relevant data from Supabase based on query analysis.
    Returns a dict with profiles, stats, or error info.
    Falls back to demo data if database is not configured.
    """
    supabase = get_supabase()
    if not supabase:
        # Use demo data when database is not configured
        from core.demo_data import query_demo_data
        logger.info("Database not configured, using demo data")
        return query_demo_data(query, limit=50)
    
    try:
        # Extract query hints
        region = extract_region(query)
        parameter = extract_parameter(query)
        
        # Build query
        query_builder = supabase.table("profiles").select(
            "id, float_id, latitude, longitude, date, cycle_number"
        ).limit(20)
        
        # Apply region filter if found
        if region:
            query_builder = query_builder.gte("latitude", region["min_lat"])
            query_builder = query_builder.lte("latitude", region["max_lat"])
            query_builder = query_builder.gte("longitude", region["min_lon"])
            query_builder = query_builder.lte("longitude", region["max_lon"])
        
        # Execute query
        result = query_builder.execute()
        profiles = result.data if result.data else []
        
        # Calculate basic stats if we have data
        stats = {}
        if profiles:
            lats = [p["latitude"] for p in profiles if p.get("latitude")]
            lons = [p["longitude"] for p in profiles if p.get("longitude")]
            
            if lats:
                stats["lat_range"] = f"{min(lats):.1f}° to {max(lats):.1f}°"
            if lons:
                stats["lon_range"] = f"{min(lons):.1f}° to {max(lons):.1f}°"
            
            # Get unique floats
            float_ids = set(p.get("float_id") for p in profiles if p.get("float_id"))
            stats["unique_floats"] = len(float_ids)
        
        return {
            "profiles": profiles,
            "count": len(profiles),
            "stats": stats,
            "region_detected": region is not None,
            "parameter_detected": parameter
        }
        
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return {"error": str(e), "profiles": []}


@router.post("/explorer", response_model=ExplorerResponse)
async def explorer_query(request: ExplorerRequest) -> ExplorerResponse:
    """
    Process a natural language query in Explorer mode.
    
    This is a simplified endpoint that:
    1. Analyzes the query for region/parameter hints
    2. Fetches relevant data from Supabase
    3. Uses LLM to generate a natural language response
    
    Falls back gracefully if LLM providers are unavailable.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"Explorer query [{request_id}]: {request.query[:100]}...")
    
    try:
        # Step 1: Fetch relevant data
        data = await fetch_data_for_query(request.query)
        
        # Step 2: Initialize LLM service with provided keys
        llm = LLMService(
            groq_api_key=request.groq_api_key,
            huggingface_api_key=request.huggingface_api_key
        )
        
        # Step 2.5: Check query complexity
        is_simple_enough, complexity_reason = is_valid_explorer_query(request.query)
        suggest_power = not is_simple_enough
        
        # Step 3: Generate response
        if suggest_power:
            # Query is too complex - provide helpful message but suggest Power Mode
            power_mode_response = (
                f"🔍 This looks like a more advanced query involving {complexity_reason}. "
                f"Explorer mode is great for quick lookups and basic exploration, but for "
                f"in-depth analysis like this, I'd recommend switching to **Power Mode**. \n\n"
                f"In Power Mode, you'll get:\n"
                f"• Full statistical analysis pipeline\n"
                f"• Custom visualizations and charts\n"
                f"• Multi-parameter comparisons\n"
                f"• Time-series and trend analysis\n\n"
                f"Switch to Power Mode in the top-right corner to explore this in depth!"
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            return ExplorerResponse(
                success=True,
                request_id=request_id,
                query=request.query,
                response=power_mode_response,
                data=None,
                confidence=0.3,
                execution_time_ms=execution_time,
                provider_used="complexity_check",
                suggest_power_mode=True,
                complexity_reason=complexity_reason
            )
        
        # Simple query - proceed with Explorer mode
        llm_result = await llm.generate_response(
            query=request.query,
            data=data if data.get("profiles") else None,
            context="Explorer mode - provide concise, beginner-friendly explanations. Keep it simple and educational."
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        return ExplorerResponse(
            success=True,
            request_id=request_id,
            query=request.query,
            response=llm_result.get("response", "Query processed."),
            data=data if data.get("profiles") else None,
            confidence=llm_result.get("confidence", 0.5),
            execution_time_ms=execution_time,
            provider_used="llm" if llm_result.get("llm_used") else "fallback",
            suggest_power_mode=False
        )
        
    except Exception as e:
        logger.error(f"Explorer query [{request_id}] failed: {e}")
        execution_time = (time.time() - start_time) * 1000
        
        return ExplorerResponse(
            success=False,
            request_id=request_id,
            query=request.query,
            response="Unable to process your query. Please try again.",
            confidence=0.0,
            execution_time_ms=execution_time,
            error=str(e)
        )


@router.get("/explorer/regions")
async def list_regions() -> Dict[str, Any]:
    """List available region mappings for query hints."""
    return {
        "regions": list(REGION_MAPPINGS.keys()),
        "hint": "Include a region name in your query for more targeted results"
    }
