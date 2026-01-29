"""
Core configuration module for FloatChat API.
Loads configuration from environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "FloatChat"
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # API Server
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=4, alias="API_WORKERS")
    
    # CORS
    cors_origins_str: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS"
    )
    
    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins_str.split(",")]
    
    # LLM Configuration - Multi-provider with failover
    # Hierarchy: Groq (primary) → HuggingFace (fallback)
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    huggingface_api_key: Optional[str] = Field(default=None, alias="HUGGINGFACE_API_KEY")
    
    # Legacy LLM keys (kept for backwards compatibility)
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    
    # Supabase
    supabase_url: Optional[str] = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: Optional[str] = Field(default=None, alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: Optional[str] = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    
    # ARGO Data Source
    gdac_url: str = Field(default="https://data-argo.ifremer.fr", alias="GDAC_URL")
    
    # Demo Mode (uses mock data when true or when DB not connected)
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    
    # ChromaDB
    chroma_host: str = Field(default="localhost", alias="CHROMA_HOST")
    chroma_port: int = Field(default=8001, alias="CHROMA_PORT")
    chroma_collection: str = Field(default="floatchat_embeddings", alias="CHROMA_COLLECTION")
    
    # RabbitMQ
    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672", alias="RABBITMQ_URL")
    rabbitmq_queue: str = Field(default="floatchat_tasks", alias="RABBITMQ_QUEUE")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=100, alias="RATE_LIMIT_PER_MINUTE")
    
    # Security
    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiry_hours: int = Field(default=24, alias="JWT_EXPIRY_HOURS")
    
    # MCP Servers
    mcp_structured_url: str = Field(default="http://localhost:8010", alias="MCP_STRUCTURED_URL")
    mcp_metadata_url: str = Field(default="http://localhost:8011", alias="MCP_METADATA_URL")
    mcp_profile_url: str = Field(default="http://localhost:8012", alias="MCP_PROFILE_URL")
    mcp_semantic_url: str = Field(default="http://localhost:8013", alias="MCP_SEMANTIC_URL")
    mcp_cache_url: str = Field(default="http://localhost:8014", alias="MCP_CACHE_URL")
    mcp_visualization_url: str = Field(default="http://localhost:8015", alias="MCP_VISUALIZATION_URL")
    
    # Feature Flags
    enable_neural_security: bool = Field(default=True, alias="ENABLE_NEURAL_SECURITY")
    enable_llm_arbitration: bool = Field(default=True, alias="ENABLE_LLM_ARBITRATION")
    enable_memory_systems: bool = Field(default=True, alias="ENABLE_MEMORY_SYSTEMS")
    enable_iterative_refinement: bool = Field(default=True, alias="ENABLE_ITERATIVE_REFINEMENT")
    
    # Monitoring
    prometheus_port: int = Field(default=9090, alias="PROMETHEUS_PORT")
    otel_exporter_endpoint: Optional[str] = Field(default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    otel_service_name: str = Field(default="floatchat", alias="OTEL_SERVICE_NAME")
    
    class Config:
        env_file = "../../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
