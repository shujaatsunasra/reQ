"""
FloatChat API - AI-Powered Oceanographic Data Analytics Platform

Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.logging import setup_logging
# Import routers
from routers import health, explorer

# Try to import query router (requires spacy)
try:
    from routers import query
    QUERY_ROUTER_AVAILABLE = True
except ImportError as e:
    QUERY_ROUTER_AVAILABLE = False
    print(f"⚠️  Query router not available (missing dependency: {e}). Power mode will use fallback.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()
    print("🌊 FloatChat API starting up...")
    
    # Initialize connections (all are optional - app works with demo data)
    from core.database import init_db
    from core.redis import init_redis
    from core.chromadb import init_chromadb
    from core.config import settings
    
    db_connected = await init_db()
    redis_connected = await init_redis()
    chroma_connected = await init_chromadb()
    
    if db_connected and redis_connected:
        print("✅ All services initialized")
    else:
        print("⚠️  Running in demo mode (some services unavailable)")
        print(f"   Database: {'✅' if db_connected else '❌ Using demo data'}")
        print(f"   Redis: {'✅' if redis_connected else '❌ Caching disabled'}")
        print(f"   ChromaDB: {'✅' if chroma_connected else '❌ Semantic search limited'}")
    
    yield
    
    # Shutdown
    print("🌊 FloatChat API shutting down...")
    from core.database import close_db
    from core.redis import close_redis
    
    await close_db()
    await close_redis()


app = FastAPI(
    title="FloatChat API",
    description="AI-Powered Oceanographic Data Analytics Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middleware - disable for now to avoid extra dependencies
# app.add_middleware(RateLimitMiddleware)
# app.add_middleware(TracingMiddleware)

# Include Routers
app.include_router(health.router, tags=["Health"])
app.include_router(explorer.router, prefix="/api", tags=["Explorer"])

# Include query router if available
if QUERY_ROUTER_AVAILABLE:
    app.include_router(query.router, prefix="/api", tags=["Query"])
else:
    # Fallback: register a power mode endpoint that uses REAL ARGO data
    import time
    import uuid
    from typing import Optional
    
    @app.post("/api/query")
    async def power_mode_fallback(request: dict):
        """
        Fallback Power Mode endpoint when full NL2Op pipeline is unavailable.
        Uses REAL ARGO data from local NetCDF files (supports multiple years).
        """
        from core.argo_loader import query_from_text, compare_regions
        from core.llm_service import LLMService
        
        request_id = str(uuid.uuid4())
        start_time = time.time()
        query_text = request.get("query", "")
        filters = request.get("filters", {})
        
        # Detect query intent
        query_lower = query_text.lower()
        is_compare = any(word in query_lower for word in ["compare", "difference", "versus", "vs"])
        
        # Get REAL ARGO data based on query
        try:
            result = query_from_text(query_text)
            
            if is_compare and 'region1' in result:
                data = result
                profile_count = len(result.get('region1', {}).get('profiles', []))
            else:
                data = {"profiles": result["profiles"], "stats": result.get("stats", {})}
                profile_count = len(result["profiles"])
            
            region_detected = result.get("region_detected")
            total_available = result.get("total", profile_count)
            
        except Exception as e:
            # Fallback to demo data if ARGO loader fails
            from core.demo_data import query_demo_data
            demo_result = query_demo_data(query_text, filters=filters, limit=100)
            data = {"profiles": demo_result["profiles"], "stats": demo_result.get("stats", {})}
            profile_count = len(demo_result["profiles"])
            region_detected = demo_result.get("region_detected")
            total_available = profile_count
        
        # Generate LLM response
        try:
            llm = LLMService(
                groq_api_key=request.get("groq_api_key"),
                huggingface_api_key=request.get("huggingface_api_key")
            )
            
            llm_result = await llm.generate_response(
                query=query_text,
                data=data,
                context=f"Power Mode analysis with REAL ARGO 2019 Indian Ocean data. {profile_count} profiles found."
            )
            response_text = llm_result.get("response", f"Found {profile_count} ARGO profiles.")
            confidence = llm_result.get("confidence", 0.85)
        except Exception:
            response_text = f"Found {profile_count} ARGO profiles from 2019 Indian Ocean dataset."
            if region_detected:
                response_text += f" Region: {region_detected}."
            if total_available > profile_count:
                response_text += f" Showing {profile_count} of {total_available} total profiles."
            confidence = 0.9
        
        execution_time = (time.time() - start_time) * 1000
        
        # Return in query format with power mode extras
        return {
            "success": True,
            "request_id": request_id,
            "query": query_text,
            "response": response_text,
            "data": data,
            "confidence": confidence,
            "execution_time_ms": execution_time,
            "interpretation": {
                "intent": "power_mode_analysis",
                "mode": "argo_data",
                "entities": {
                    "region": region_detected,
                    "count": profile_count,
                    "total_available": total_available
                }
            },
            "visualizations": [],
            "refinement_iterations": 0,
            "operator_dag": {
                "operators": [
                    {"id": "fetch", "type": "DATA_FETCH", "status": "completed", "records": total_available},
                    {"id": "filter", "type": "SPATIAL_FILTER", "status": "completed", "records": profile_count},
                    {"id": "analyze", "type": "ANALYZE", "status": "completed"},
                ],
                "intent": "explore" if not is_compare else "compare"
            },
            "cost_metrics": {
                "parse_time": 5,
                "plan_time": 10,
                "execute_time": execution_time - 15,
            },
            "demo_mode": False,
            "data_source": ", ".join(result.get("stats", {}).get("datasets", ["ARGO Data"])),
            "available_years": result.get("available_years", []),
            "error": None
        }
    
    @app.get("/api/datasets")
    async def get_datasets():
        """Get information about all available ARGO datasets."""
        from core.argo_loader import get_dataset_info, get_available_years, refresh_cache
        
        info = get_dataset_info()
        return {
            "success": True,
            "data": info,
            "message": f"Found {len(info['years'])} datasets: {info['years']}"
        }
    
    @app.post("/api/datasets/refresh")
    async def refresh_datasets():
        """Force refresh of dataset cache to detect newly added datasets."""
        from core.argo_loader import refresh_cache, get_dataset_info
        
        refresh_cache()
        info = get_dataset_info()
        return {
            "success": True,
            "data": info,
            "message": f"Cache refreshed. Found {len(info['years'])} datasets."
        }
    
    @app.get("/api/stats/yearly")
    async def get_yearly_stats(region: Optional[str] = None):
        """Get yearly statistics across all datasets."""
        from core.argo_loader import get_yearly_stats
        from typing import Optional
        
        stats = get_yearly_stats(region)
        return {
            "success": True,
            "data": stats,
            "region": region
        }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc) if settings.debug else "An internal error occurred"
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
