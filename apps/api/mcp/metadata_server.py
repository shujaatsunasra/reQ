"""
MetadataProcessingServer - Handles file index and metadata operations.
"""

from typing import List, Dict, Any
import time

from core.logging import get_logger
from core.database import execute_query
from .base import MCPServer, MCPRequest, MCPResponse

logger = get_logger(__name__)


class MetadataProcessingServer(MCPServer):
    """
    MCP Server for metadata and file index operations.
    
    Handles:
    - File index queries
    - Metadata extraction
    - JSONB operations
    """
    
    def __init__(self):
        super().__init__("metadata")
    
    def get_operations(self) -> List[str]:
        return [
            "query_file_index",
            "get_metadata",
            "search_metadata",
            "get_float_info",
            "get_data_centers"
        ]
    
    async def execute(self, request: MCPRequest) -> MCPResponse:
        start_time = time.time()
        
        error = await self._validate_request(request)
        if error:
            return self._error_response(
                request.request_id,
                "VALIDATION_ERROR",
                error,
                (time.time() - start_time) * 1000
            )
        
        try:
            if request.operation == "query_file_index":
                result = await self._query_file_index(request.params)
            elif request.operation == "get_metadata":
                result = await self._get_metadata(request.params)
            elif request.operation == "search_metadata":
                result = await self._search_metadata(request.params)
            elif request.operation == "get_float_info":
                result = await self._get_float_info(request.params)
            elif request.operation == "get_data_centers":
                result = await self._get_data_centers(request.params)
            else:
                result = {"data": [], "count": 0}
            
            return self._success_response(
                request.request_id,
                result.get("data"),
                (time.time() - start_time) * 1000,
                {"rows_count": result.get("count", 0)}
            )
            
        except Exception as e:
            self.logger.error(f"Operation {request.operation} failed: {e}")
            return self._error_response(
                request.request_id,
                "EXECUTION_ERROR",
                str(e),
                (time.time() - start_time) * 1000
            )
    
    async def _query_file_index(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query the file index table."""
        float_id = params.get("float_id")
        data_center = params.get("data_center")
        time_range = params.get("time_range")
        bbox = params.get("bbox")
        
        conditions = []
        query_params = []
        param_idx = 1
        
        if float_id:
            conditions.append(f"float_id = ${param_idx}")
            query_params.append(float_id)
            param_idx += 1
        
        if data_center:
            conditions.append(f"data_center = ${param_idx}")
            query_params.append(data_center)
            param_idx += 1
        
        if time_range and len(time_range) == 2:
            conditions.append(f"time_start <= ${param_idx} AND time_end >= ${param_idx+1}")
            query_params.extend([time_range[1], time_range[0]])
            param_idx += 2
        
        if bbox and len(bbox) == 4:
            conditions.append(f"""
                lon_min <= ${param_idx+2} AND lon_max >= ${param_idx} AND
                lat_min <= ${param_idx+3} AND lat_max >= ${param_idx+1}
            """)
            query_params.extend(bbox)
            param_idx += 4
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        query = f"""
            SELECT 
                float_id, data_center, file_path,
                time_start, time_end,
                lat_min, lat_max, lon_min, lon_max,
                depth_min, depth_max,
                metadata
            FROM file_index
            WHERE {where_clause}
            LIMIT 500
        """
        
        try:
            rows = await execute_query(query, *query_params)
            return {"data": rows, "count": len(rows)}
        except Exception as e:
            self.logger.warning(f"Database query failed: {e}")
            return {"data": [], "count": 0}
    
    async def _get_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata for a specific profile or float."""
        profile_id = params.get("profile_id")
        float_id = params.get("float_id")
        
        if profile_id:
            query = """
                SELECT metadata
                FROM profiles
                WHERE profile_id = $1
            """
            try:
                rows = await execute_query(query, profile_id)
                return {"data": rows[0] if rows else None, "count": len(rows)}
            except Exception:
                return {"data": None, "count": 0}
        
        elif float_id:
            query = """
                SELECT metadata
                FROM file_index
                WHERE float_id = $1
                LIMIT 1
            """
            try:
                rows = await execute_query(query, float_id)
                return {"data": rows[0] if rows else None, "count": len(rows)}
            except Exception:
                return {"data": None, "count": 0}
        
        return {"data": None, "count": 0}
    
    async def _search_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search within metadata JSONB fields."""
        key = params.get("key")
        value = params.get("value")
        
        if not key:
            return {"data": [], "count": 0}
        
        query = """
            SELECT float_id, metadata
            FROM file_index
            WHERE metadata->$1 @> $2::jsonb
            LIMIT 100
        """
        
        try:
            import json
            rows = await execute_query(query, key, json.dumps(value))
            return {"data": rows, "count": len(rows)}
        except Exception as e:
            self.logger.warning(f"Metadata search failed: {e}")
            return {"data": [], "count": 0}
    
    async def _get_float_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive information about a float."""
        float_id = params.get("float_id")
        
        if not float_id:
            return {"data": None, "count": 0}
        
        query = """
            SELECT 
                f.float_id,
                f.data_center,
                f.metadata,
                COUNT(p.profile_id) as profile_count,
                MIN(p.timestamp) as first_profile,
                MAX(p.timestamp) as last_profile
            FROM file_index f
            LEFT JOIN profiles p ON f.float_id = p.float_id
            WHERE f.float_id = $1
            GROUP BY f.float_id, f.data_center, f.metadata
        """
        
        try:
            rows = await execute_query(query, float_id)
            return {"data": rows[0] if rows else None, "count": len(rows)}
        except Exception:
            return {"data": None, "count": 0}
    
    async def _get_data_centers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of data centers with float counts."""
        query = """
            SELECT 
                data_center,
                COUNT(DISTINCT float_id) as float_count
            FROM file_index
            GROUP BY data_center
            ORDER BY float_count DESC
        """
        
        try:
            rows = await execute_query(query)
            return {"data": rows, "count": len(rows)}
        except Exception:
            return {"data": [], "count": 0}
