"""
LLM Service - Multi-provider implementation with failover support.
Provider Hierarchy: Groq (primary) → HuggingFace (fallback) → Graceful failure
"""

import httpx
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import json

from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)


# ============================================================================
# Provider Types & Schemas
# ============================================================================

class ProviderType(str, Enum):
    GROQ = "groq"
    HUGGINGFACE = "huggingface"


@dataclass
class ProviderResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ProviderHealthStatus:
    """Health status of a provider."""
    is_healthy: bool = True
    last_error: Optional[str] = None
    last_checked: datetime = field(default_factory=datetime.now)
    response_time_ms: Optional[float] = None


# ============================================================================
# Provider Interface
# ============================================================================

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    name: ProviderType
    health_status: ProviderHealthStatus
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is available."""
        pass
    
    @abstractmethod
    async def generate_response(self, prompt: str) -> ProviderResponse:
        """Generate a response from the prompt."""
        pass
    
    def get_health_status(self) -> ProviderHealthStatus:
        """Get the current health status."""
        return self.health_status


# ============================================================================
# Groq Provider Implementation
# ============================================================================

class GroqProvider(LLMProvider):
    """Groq provider - Primary, fastest option."""
    
    name = ProviderType.GROQ
    BASE_URL = "https://api.groq.com/openai/v1"
    MODEL = "llama-3.1-8b-instant"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.health_status = ProviderHealthStatus()
    
    async def is_available(self) -> bool:
        """Check if Groq API is available."""
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=5.0
                )
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            is_healthy = response.status_code == 200
            
            self.health_status = ProviderHealthStatus(
                is_healthy=is_healthy,
                last_checked=datetime.now(),
                response_time_ms=response_time,
                last_error=None if is_healthy else f"HTTP {response.status_code}"
            )
            
            return is_healthy
            
        except Exception as e:
            self.health_status = ProviderHealthStatus(
                is_healthy=False,
                last_checked=datetime.now(),
                last_error=str(e)
            )
            return False
    
    async def generate_response(self, prompt: str) -> ProviderResponse:
        """Generate response using Groq API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2048,
                        "temperature": 0.1,
                        "stream": False
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
            
            usage = data.get("usage", {})
            
            return ProviderResponse(
                content=data["choices"][0]["message"]["content"],
                model=self.MODEL,
                provider=self.name.value,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0)
            )
            
        except Exception as e:
            self.health_status.is_healthy = False
            self.health_status.last_error = str(e)
            raise


# ============================================================================
# HuggingFace Provider Implementation
# ============================================================================

class HuggingFaceProvider(LLMProvider):
    """HuggingFace provider - Fallback option."""
    
    name = ProviderType.HUGGINGFACE
    BASE_URL = "https://api-inference.huggingface.co/models"
    MODEL = "microsoft/DialoGPT-large"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.health_status = ProviderHealthStatus()
    
    async def is_available(self) -> bool:
        """Check if HuggingFace API is available."""
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/{self.MODEL}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "inputs": "test",
                        "options": {"wait_for_model": False}
                    },
                    timeout=5.0
                )
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            # 503 is acceptable - means model is loading
            is_healthy = response.status_code in (200, 503)
            
            self.health_status = ProviderHealthStatus(
                is_healthy=is_healthy,
                last_checked=datetime.now(),
                response_time_ms=response_time,
                last_error=None if is_healthy else f"HTTP {response.status_code}"
            )
            
            return is_healthy
            
        except Exception as e:
            self.health_status = ProviderHealthStatus(
                is_healthy=False,
                last_checked=datetime.now(),
                last_error=str(e)
            )
            return False
    
    async def generate_response(self, prompt: str) -> ProviderResponse:
        """Generate response using HuggingFace Inference API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/{self.MODEL}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "inputs": prompt,
                        "parameters": {
                            "max_new_tokens": 500,
                            "temperature": 0.1,
                            "return_full_text": False
                        },
                        "options": {"wait_for_model": True}
                    },
                    timeout=60.0  # Longer timeout for model loading
                )
                response.raise_for_status()
                data = response.json()
            
            # HuggingFace returns array or object
            if isinstance(data, list):
                content = data[0].get("generated_text", "") if data else ""
            else:
                content = data.get("generated_text", "")
            
            return ProviderResponse(
                content=content.strip(),
                model=self.MODEL,
                provider=self.name.value
            )
            
        except Exception as e:
            self.health_status.is_healthy = False
            self.health_status.last_error = str(e)
            raise


# ============================================================================
# Response Validator - Anti-Hallucination Guards
# ============================================================================

class ResponseValidator:
    """Validates LLM responses to prevent hallucinations."""
    
    # Obvious template patterns to reject
    TEMPLATE_PATTERNS = [
        r"^here's a fun fact about",
        r"^did you know that the ocean",
        r"this is a placeholder",
        r"lorem ipsum",
        r"sample data shows",
    ]
    
    # Hardcoded response fragments to reject
    HARDCODED_FRAGMENTS = [
        "this is sample data",
        "placeholder response",
        "mock analysis",
    ]
    
    # Patterns that indicate real data references
    DATA_PATTERNS = [
        r"\d+\.\d+°",                    # Coordinates
        r"\d+\s*(?:°C|celsius|temp)",    # Temperature
        r"\d+\s*(?:m|meters|depth)",     # Depth
        r"\d+\s*(?:psu|salinity)",       # Salinity
        r"\d{4}-\d{2}-\d{2}",            # Dates
        r"profile\s*\d+",                # Profile IDs
        r"float\s*\d+",                  # Float IDs
    ]
    
    @classmethod
    def validate_response(cls, response: str, has_real_data: bool) -> bool:
        """
        Validate that response is not a template/hallucination.
        
        Args:
            response: The LLM response text
            has_real_data: Whether real data was provided to the LLM
        
        Returns:
            True if response is valid, False if it should be rejected
        """
        if not has_real_data:
            logger.warning("⚠️ Response rejected: no real data flag")
            return False
        
        response_lower = response.lower()
        
        # Check for template patterns
        for pattern in cls.TEMPLATE_PATTERNS:
            if re.search(pattern, response_lower):
                logger.warning(f"⚠️ Response rejected: template pattern detected")
                return False
        
        # Check for hardcoded fragments
        for fragment in cls.HARDCODED_FRAGMENTS:
            if fragment in response_lower:
                logger.warning(f"⚠️ Response rejected: hardcoded fragment detected")
                return False
        
        return True
    
    @classmethod
    def contains_real_data_references(cls, response: str) -> bool:
        """Check if response references actual data values."""
        for pattern in cls.DATA_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        return False


# ============================================================================
# Provider Controller - Manages Hierarchy & Failover
# ============================================================================

@dataclass
class FailureLogEntry:
    """Log entry for provider failures."""
    provider: str
    error: str
    timestamp: datetime


class LLMProviderController:
    """
    Controls LLM provider hierarchy with automatic failover.
    
    Hierarchy: Groq → HuggingFace → Graceful failure
    """
    
    GRACEFUL_FAILURE_MESSAGE = "System currently unable to generate result. Please retry."
    
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        huggingface_api_key: Optional[str] = None
    ):
        self.providers: List[LLMProvider] = []
        self.failure_log: List[FailureLogEntry] = []
        
        logger.info("🔧 LLMController initializing...")
        
        # Initialize providers in hierarchy order
        if groq_api_key and groq_api_key.strip() and groq_api_key != "your_groq_api_key_here":
            logger.info("✅ Adding Groq provider")
            self.providers.append(GroqProvider(groq_api_key))
        else:
            logger.warning("❌ Groq provider not added - API key missing")
        
        if huggingface_api_key and huggingface_api_key.strip() and huggingface_api_key != "your_huggingface_api_key_here":
            logger.info("✅ Adding HuggingFace provider")
            self.providers.append(HuggingFaceProvider(huggingface_api_key))
        else:
            logger.warning("❌ HuggingFace provider not added - API key missing")
        
        logger.info(f"📊 Total providers configured: {len(self.providers)}")
        
        if not self.providers:
            logger.warning("⚠️ No LLM providers configured. System will return graceful failure messages.")
    
    async def generate_response(self, prompt: str) -> str:
        """
        Generate response using provider hierarchy.
        Tries Groq first, falls back to HuggingFace, then graceful failure.
        """
        if not self.providers:
            return self.GRACEFUL_FAILURE_MESSAGE
        
        last_error = ""
        
        for provider in self.providers:
            try:
                logger.info(f"🔄 Attempting to use {provider.name.value} provider...")
                
                response = await provider.generate_response(prompt)
                
                logger.info(f"✅ Successfully generated response using {provider.name.value}")
                
                if last_error:
                    logger.info(f"✅ Failover successful: {provider.name.value} recovered after failure")
                
                return response.content
                
            except Exception as e:
                error_message = str(e)
                last_error = error_message
                
                # Log the failure
                self.failure_log.append(FailureLogEntry(
                    provider=provider.name.value,
                    error=error_message,
                    timestamp=datetime.now()
                ))
                
                logger.error(f"❌ {provider.name.value} provider failed: {error_message}")
                continue
        
        # All providers failed
        logger.error("❌ All LLM providers failed. Returning graceful failure message.")
        return self.GRACEFUL_FAILURE_MESSAGE
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status."""
        return {
            "providers": [
                {
                    "name": p.name.value,
                    "is_healthy": p.health_status.is_healthy,
                    "last_error": p.health_status.last_error,
                    "last_checked": p.health_status.last_checked.isoformat(),
                    "response_time_ms": p.health_status.response_time_ms
                }
                for p in self.providers
            ],
            "recent_failures": [
                {
                    "provider": f.provider,
                    "error": f.error,
                    "timestamp": f.timestamp.isoformat()
                }
                for f in self.failure_log[-10:]  # Last 10 failures
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    async def test_all_providers(self) -> Dict[str, bool]:
        """Test all providers and return availability status."""
        results = {}
        for provider in self.providers:
            results[provider.name.value] = await provider.is_available()
        return results


# ============================================================================
# LLM Service - High-level API for Query Processing
# ============================================================================

class LLMService:
    """
    High-level LLM service for oceanographic query processing.
    Uses LLMProviderController for multi-provider support with failover.
    """
    
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        huggingface_api_key: Optional[str] = None
    ):
        # Get API keys from settings if not provided
        groq_key = groq_api_key or getattr(settings, 'groq_api_key', None)
        hf_key = huggingface_api_key or getattr(settings, 'huggingface_api_key', None)
        
        self.controller = LLMProviderController(
            groq_api_key=groq_key,
            huggingface_api_key=hf_key
        )
    
    async def generate_response(
        self,
        query: str,
        data: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a natural language response for a query.
        
        Args:
            query: User's natural language query
            data: Retrieved oceanographic data
            context: Additional context (intent, etc.)
            conversation_history: Previous messages for context [{"role": str, "content": str}]
        
        Returns:
            Dict with response, confidence, and metadata
        """
        has_real_data = bool(data)
        
        # Build the prompt with conversation history
        prompt = self._build_prompt(query, data, context, conversation_history)
        
        # Generate response via provider controller
        response_text = await self.controller.generate_response(prompt)
        
        # Check for graceful failure
        if response_text == LLMProviderController.GRACEFUL_FAILURE_MESSAGE:
            return {
                "response": self._generate_fallback_response(query, data),
                "confidence": 0.3,
                "llm_used": False,
                "error": "All providers unavailable"
            }
        
        # Validate response if we have real data
        if has_real_data:
            is_valid = ResponseValidator.validate_response(response_text, has_real_data)
            if not is_valid:
                return {
                    "response": self._generate_fallback_response(query, data),
                    "confidence": 0.4,
                    "llm_used": True,
                    "validation_failed": True
                }
        
        return {
            "response": response_text,
            "confidence": 0.9 if has_real_data else 0.7,
            "llm_used": True,
            "has_data_references": ResponseValidator.contains_real_data_references(response_text)
        }
    
    def _build_prompt(
        self,
        query: str,
        data: Optional[Dict[str, Any]],
        context: Optional[str],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Build an enhanced prompt with rich contextual awareness for the LLM."""
        
        # Rich system prompt with balanced behavior
        system_prompt = """You are FloatChat, a friendly AI assistant specialized in oceanographic data exploration.

## CRITICAL BEHAVIOR RULES
1. **Match the user's intent**: If they say "hi" or "how are you", respond casually - DO NOT analyze data.
2. **Only discuss data when relevant**: Only analyze ocean data if the user asks about it AND data is provided.
3. **No data = simple response**: If there's no data or the query is casual, give a brief, natural response.
4. **Never invent patterns**: Only discuss statistics from the actual data provided.
5. **NEVER mention technical tools**: Do NOT mention Matplotlib, Plotly, Python, GMT, libraries, or any implementation details. Just describe the data and insights.
6. **Use conversation history**: Refer to previous messages to maintain context and provide relevant follow-up responses.

## For Casual Messages (greetings, how are you, etc.)
- Respond briefly and naturally
- DO NOT discuss ARGO floats, temperatures, or data analysis
- Just be friendly!

## For Data Queries (when user asks about ocean data AND data is provided)
- Summarize key findings concisely (2-4 sentences)
- Mention specific numbers from the data
- Connect to real oceanographic phenomena when relevant
- If visualizations are shown, describe what they reveal - NOT how they were made

## For Follow-up Questions
- Reference previous discussion naturally
- Build on previous findings
- Don't repeat information already given

## FORBIDDEN Topics (NEVER mention these)
- Library names (Matplotlib, Plotly, Recharts, D3, etc.)
- Programming languages (Python, JavaScript, etc.)
- Technical tools (GMT, QGIS, etc.)
- Implementation details ("I would recommend using...")
- Code or algorithms

## Response Length
- Casual messages: 1-2 sentences max
- Data queries: 2-4 sentences with key findings"""

        parts = [system_prompt]
        
        # Add conversation history for context
        if conversation_history:
            parts.append("\n## Conversation History:")
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # Truncate long messages
                if len(content) > 500:
                    content = content[:500] + "..."
                parts.append(f"{role.upper()}: {content}")
            parts.append("")
        
        parts.append(f"\nCurrent User Query: {query}")
        
        if data:
            summary = self._summarize_data_enhanced(data)
            parts.append(f"\nRetrieved Data:\n{summary}")
        else:
            parts.append("\nNo data was retrieved for this query.")
        
        if context:
            parts.append(f"\nAdditional Context: {context}")
        
        parts.append("\nProvide a helpful, contextually-aware response:")
        
        return "\n".join(parts)
    
    def _summarize_data_enhanced(self, data: Dict[str, Any]) -> str:
        """Create a comprehensive data summary for the prompt."""
        if not data:
            return "No data"
        
        parts = []
        
        if "profiles" in data:
            profiles = data["profiles"]
            count = len(profiles)
            parts.append(f"• {count} ARGO float profiles found")
            
            if count > 0:
                # Extract key statistics
                temps = [p.get('temp', p.get('temperature')) for p in profiles if p.get('temp') or p.get('temperature')]
                salinities = [p.get('salinity') for p in profiles if p.get('salinity')]
                depths = [p.get('depth') for p in profiles if p.get('depth')]
                
                if temps:
                    temps = [t for t in temps if t is not None]
                    if temps:
                        parts.append(f"• Temperature range: {min(temps):.1f}°C to {max(temps):.1f}°C (avg: {sum(temps)/len(temps):.1f}°C)")
                
                if salinities:
                    salinities = [s for s in salinities if s is not None]
                    if salinities:
                        parts.append(f"• Salinity range: {min(salinities):.1f} to {max(salinities):.1f} PSU (avg: {sum(salinities)/len(salinities):.1f} PSU)")
                
                if depths:
                    depths = [d for d in depths if d is not None]
                    if depths:
                        parts.append(f"• Depth range: {min(depths)}m to {max(depths)}m")
                
                # Geographic coverage
                lats = [p.get('latitude', p.get('lat')) for p in profiles if p.get('latitude') or p.get('lat')]
                lngs = [p.get('longitude', p.get('lng')) for p in profiles if p.get('longitude') or p.get('lng')]
                if lats and lngs:
                    lats = [l for l in lats if l is not None]
                    lngs = [l for l in lngs if l is not None]
                    if lats and lngs:
                        parts.append(f"• Geographic extent: {min(lats):.1f}°N to {max(lats):.1f}°N, {min(lngs):.1f}°E to {max(lngs):.1f}°E")
                
                # Sample profiles for specificity
                if count <= 5:
                    for p in profiles[:3]:
                        lat = p.get('latitude', p.get('lat'))
                        lon = p.get('longitude', p.get('lng'))
                        temp = p.get('temp', p.get('temperature'))
                        float_id = p.get('float_id', p.get('id', 'unknown'))
                        loc = f"at ({lat:.1f}°, {lon:.1f}°)" if lat and lon else ""
                        temp_str = f", {temp:.1f}°C" if temp else ""
                        parts.append(f"  - Float {float_id} {loc}{temp_str}")
        
        if "count" in data:
            parts.append(f"• Total records: {data['count']}")
        
        if "stats" in data:
            stats = data["stats"]
            if "avg_temp" in stats:
                parts.append(f"• Average temperature: {stats['avg_temp']:.2f}°C")
            if "avg_salinity" in stats:
                parts.append(f"• Average salinity: {stats['avg_salinity']:.2f} PSU")
            if "date_range" in stats:
                parts.append(f"• Date range: {stats['date_range']}")
        
        return "\n".join(parts) if parts else json.dumps(data)[:800]
    
    def _summarize_data(self, data: Dict[str, Any]) -> str:
        """Create a concise data summary for the prompt."""
        if not data:
            return "No data"
        
        parts = []
        
        if "profiles" in data:
            profiles = data["profiles"]
            count = len(profiles)
            parts.append(f"{count} profiles found")
            
            if count > 0 and count <= 5:
                for p in profiles[:3]:
                    lat = p.get('latitude', p.get('lat'))
                    lon = p.get('longitude', p.get('lng'))
                    loc = f"({lat:.1f}°, {lon:.1f}°)" if lat and lon else ""
                    float_id = p.get('float_id', p.get('id', 'unknown'))
                    parts.append(f"Float {float_id} {loc}")
        
        if "count" in data:
            parts.append(f"Total records: {data['count']}")
        
        if "stats" in data:
            stats = data["stats"]
            if "avg_temp" in stats:
                parts.append(f"Avg temp: {stats['avg_temp']:.1f}°C")
            if "avg_salinity" in stats:
                parts.append(f"Avg salinity: {stats['avg_salinity']:.1f} PSU")
        
        return "; ".join(parts) if parts else json.dumps(data)[:500]
    
    def _generate_fallback_response(
        self,
        query: str,
        data: Optional[Dict[str, Any]]
    ) -> str:
        """Generate fallback response without LLM."""
        if not data:
            return "No data found for your query. Try specifying a region (e.g., 'Arabian Sea') or time period."
        
        if isinstance(data, dict):
            if "profiles" in data:
                count = len(data["profiles"])
                if count > 0:
                    return f"Found {count} ARGO float profiles matching your query."
                return "No profiles match your criteria. Try adjusting the region or time range."
            
            if "count" in data:
                return f"Found {data['count']} records matching your query."
        
        return "Query processed successfully."
    
    def get_health(self) -> Dict[str, Any]:
        """Get LLM system health status."""
        return self.controller.get_system_health()
    
    async def test_providers(self) -> Dict[str, bool]:
        """Test all LLM providers."""
        return await self.controller.test_all_providers()


# ============================================================================
# Service Factory
# ============================================================================

_llm_service: Optional[LLMService] = None


def get_llm_service(
    api_key: Optional[str] = None,
    provider: Optional[str] = None
) -> LLMService:
    """
    Get or create LLM service instance.
    
    Args:
        api_key: API key (applied to primary provider if specified)
        provider: Provider hint (ignored - uses hierarchy)
    
    Returns:
        LLMService instance
    """
    global _llm_service
    
    # If API key provided, create new service with that key for Groq
    if api_key:
        return LLMService(groq_api_key=api_key)
    
    # Use singleton
    if _llm_service is None:
        _llm_service = LLMService()
    
    return _llm_service