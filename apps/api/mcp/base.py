"""
MCP Server base class and common types.
"""

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import time
import uuid

from core.logging import get_logger

logger = get_logger(__name__)


class MCPRequest(BaseModel):
    """Standard MCP server request."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operation: str = Field(..., description="Operation to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")
    timeout: int = Field(default=5000, description="Timeout in milliseconds")
    trace_id: Optional[str] = Field(default=None, description="Distributed trace ID")


class MCPResponse(BaseModel):
    """Standard MCP server response."""
    success: bool = Field(..., description="Whether operation succeeded")
    request_id: str = Field(..., description="Original request ID")
    data: Optional[Any] = Field(default=None, description="Response data")
    error: Optional[Dict[str, str]] = Field(default=None, description="Error details if failed")
    execution_time_ms: float = Field(default=0.0, description="Execution time")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class MCPServer(ABC):
    """
    Abstract base class for MCP servers.
    
    All MCP servers must implement:
    - execute(): Main operation handler
    - get_operations(): List of supported operations
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"mcp.{name}")
    
    @abstractmethod
    async def execute(self, request: MCPRequest) -> MCPResponse:
        """Execute an operation and return response."""
        pass
    
    @abstractmethod
    def get_operations(self) -> List[str]:
        """Get list of supported operations."""
        pass
    
    def _success_response(
        self,
        request_id: str,
        data: Any,
        execution_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """Create a success response."""
        return MCPResponse(
            success=True,
            request_id=request_id,
            data=data,
            execution_time_ms=execution_time,
            metadata=metadata
        )
    
    def _error_response(
        self,
        request_id: str,
        code: str,
        message: str,
        execution_time: float
    ) -> MCPResponse:
        """Create an error response."""
        return MCPResponse(
            success=False,
            request_id=request_id,
            error={"code": code, "message": message},
            execution_time_ms=execution_time
        )
    
    async def _validate_request(self, request: MCPRequest) -> Optional[str]:
        """
        Validate request. Returns error message if invalid, None if valid.
        Override in subclasses for custom validation.
        """
        if request.operation not in self.get_operations():
            return f"Unknown operation: {request.operation}"
        return None
