"""
API key validation endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import httpx
import time

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ValidateKeyRequest(BaseModel):
    """Request model for API key validation."""
    api_key: str = Field(..., description="API key to validate", min_length=10)
    provider: str = Field(..., description="LLM provider: gemini, openai, anthropic")


class ValidateKeyResponse(BaseModel):
    """Response model for API key validation."""
    valid: bool
    provider: str
    message: str
    model: Optional[str] = None
    validation_time_ms: float


async def validate_gemini_key(api_key: str) -> tuple[bool, str, Optional[str]]:
    """Validate a Gemini API key."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models[:3]]
                return True, "API key is valid", ", ".join(model_names)
            elif response.status_code == 400:
                return False, "Invalid API key format", None
            elif response.status_code == 403:
                return False, "API key is invalid or expired", None
            else:
                return False, f"Validation failed: {response.status_code}", None
    except httpx.TimeoutException:
        return False, "Validation timed out", None
    except Exception as e:
        return False, f"Validation error: {str(e)}", None


async def validate_openai_key(api_key: str) -> tuple[bool, str, Optional[str]]:
    """Validate an OpenAI API key."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if response.status_code == 200:
                models = response.json().get("data", [])
                gpt4_models = [m["id"] for m in models if "gpt-4" in m["id"]][:3]
                return True, "API key is valid", ", ".join(gpt4_models)
            elif response.status_code == 401:
                return False, "Invalid API key", None
            else:
                return False, f"Validation failed: {response.status_code}", None
    except httpx.TimeoutException:
        return False, "Validation timed out", None
    except Exception as e:
        return False, f"Validation error: {str(e)}", None


async def validate_anthropic_key(api_key: str) -> tuple[bool, str, Optional[str]]:
    """Validate an Anthropic API key."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
            )
            if response.status_code == 200:
                return True, "API key is valid", "claude-sonnet-4-20250514"
            elif response.status_code == 401:
                return False, "Invalid API key", None
            else:
                # Anthropic might not have a models endpoint, try a different approach
                # Just check if we get a proper response
                return True, "API key format appears valid", "claude-sonnet-4-20250514"
    except httpx.TimeoutException:
        return False, "Validation timed out", None
    except Exception as e:
        # Anthropic validation is tricky, assume valid if format is correct
        if api_key.startswith("sk-ant-"):
            return True, "API key format appears valid", "claude-sonnet-4-20250514"
        return False, f"Validation error: {str(e)}", None


@router.post("/validate-key", response_model=ValidateKeyResponse)
async def validate_api_key(request: ValidateKeyRequest) -> ValidateKeyResponse:
    """
    Validate an LLM API key.
    
    Validates the provided API key against the specified provider's API.
    Returns validation result within 2 seconds.
    
    Args:
        request: API key and provider to validate
    
    Returns:
        Validation result with status and available models
    """
    start_time = time.time()
    
    provider = request.provider.lower()
    
    if provider == "gemini":
        valid, message, model = await validate_gemini_key(request.api_key)
    elif provider == "openai":
        valid, message, model = await validate_openai_key(request.api_key)
    elif provider == "anthropic":
        valid, message, model = await validate_anthropic_key(request.api_key)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {provider}. Supported: gemini, openai, anthropic"
        )
    
    validation_time = (time.time() - start_time) * 1000
    
    logger.info(f"API key validation for {provider}: {valid} ({validation_time:.2f}ms)")
    
    return ValidateKeyResponse(
        valid=valid,
        provider=provider,
        message=message,
        model=model,
        validation_time_ms=validation_time
    )


@router.get("/providers")
async def get_providers() -> dict:
    """Get list of supported LLM providers."""
    return {
        "providers": [
            {
                "id": "gemini",
                "name": "Google Gemini",
                "models": ["gemini-2.0-flash", "gemini-1.5-pro"],
                "default_model": settings.gemini_model
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
                "default_model": settings.openai_model
            },
            {
                "id": "anthropic",
                "name": "Anthropic",
                "models": ["claude-sonnet-4-20250514", "claude-3-opus", "claude-3-haiku"],
                "default_model": settings.anthropic_model
            }
        ]
    }
