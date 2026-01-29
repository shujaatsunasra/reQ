"""
Health check endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import time

from core.database import get_supabase, get_pg_pool
from core.redis import get_redis
from core.chromadb import get_chroma

router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str
    timestamp: float
    services: Dict[str, Any]
    version: str = "1.0.0"


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """
    Health check endpoint for Kubernetes probes.
    Returns status of all dependent services.
    """
    services = {}
    overall_status = "healthy"
    
    # Check Supabase
    supabase = get_supabase()
    services["supabase"] = {
        "status": "connected" if supabase else "not_configured",
        "healthy": supabase is not None
    }
    
    # Check PostgreSQL
    pg_pool = await get_pg_pool()
    services["postgresql"] = {
        "status": "connected" if pg_pool else "not_configured",
        "healthy": pg_pool is not None
    }
    
    # Check Redis
    redis_client = get_redis()
    if redis_client:
        try:
            await redis_client.ping()
            services["redis"] = {"status": "connected", "healthy": True}
        except Exception as e:
            services["redis"] = {"status": "error", "healthy": False, "error": str(e)}
            overall_status = "degraded"
    else:
        services["redis"] = {"status": "not_configured", "healthy": False}
    
    # Check ChromaDB
    chroma = get_chroma()
    if chroma:
        try:
            chroma.heartbeat()
            services["chromadb"] = {"status": "connected", "healthy": True}
        except Exception as e:
            services["chromadb"] = {"status": "error", "healthy": False, "error": str(e)}
            overall_status = "degraded"
    else:
        services["chromadb"] = {"status": "not_configured", "healthy": False}
    
    # Determine overall status
    required_services = ["postgresql", "redis"]
    for svc in required_services:
        if svc in services and not services[svc].get("healthy"):
            overall_status = "unhealthy"
            break
    
    return HealthStatus(
        status=overall_status,
        timestamp=time.time(),
        services=services
    )


@router.get("/ready")
async def readiness_check() -> dict:
    """
    Readiness check for Kubernetes.
    Returns 200 if the service is ready to accept traffic.
    """
    # Check critical dependencies
    pg_pool = await get_pg_pool()
    redis_client = get_redis()
    
    if pg_pool and redis_client:
        return {"ready": True}
    
    return {"ready": False, "reason": "Required services not available"}


@router.get("/live")
async def liveness_check() -> dict:
    """
    Liveness check for Kubernetes.
    Returns 200 if the service is alive.
    """
    return {"alive": True}


@router.get("/llm-health")
async def llm_health_check() -> dict:
    """
    Health check for LLM providers.
    Returns status and availability of all configured providers.
    """
    from core.llm_service import get_llm_service
    
    llm = get_llm_service()
    health = llm.get_health()
    availability = await llm.test_providers()
    
    return {
        "providers": health["providers"],
        "availability": availability,
        "recent_failures": health["recent_failures"],
        "timestamp": health["timestamp"]
    }
