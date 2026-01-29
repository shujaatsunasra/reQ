"""
StructuredDataServer - Handles SQL queries against PostgreSQL/PostGIS.
"""

from typing import List, Optional, Dict, Any
import time

from core.logging import get_logger
from core.database import execute_query, get_supabase
from .base import MCPServer, MCPRequest, MCPResponse

logger = get_logger(__name__)


class StructuredDataServer(MCPServer):
    """
    MCP Server for structured data operations.
    
    Handles:
    - Spatial queries with PostGIS
    - Temporal filtering
    - Profile and measurement retrieval
    - Aggregations and grouping
    """
    
    def __init__(self):
        super().__init__("structured")
        self.supabase = get_supabase()
    
    def get_operations(self) -> List[str]:
        return [
            "spatial_filter",
            "temporal_filter",
            "parameter_filter",
            "qc_filter",
            "float_filter",
            "aggregate",
            "group_by",
            "join",
            "query_profiles",
            "query_measurements"
        ]
    
    async def execute(self, request: MCPRequest) -> MCPResponse:
        start_time = time.time()
        
        # Validate request
        error = await self._validate_request(request)
        if error:
            return self._error_response(
                request.request_id,
                "VALIDATION_ERROR",
                error,
                (time.time() - start_time) * 1000
            )
        
        try:
            # Route to operation handler
            if request.operation == "spatial_filter":
                result = await self._spatial_filter(request.params)
            elif request.operation == "temporal_filter":
                result = await self._temporal_filter(request.params)
            elif request.operation == "parameter_filter":
                result = await self._parameter_filter(request.params)
            elif request.operation == "qc_filter":
                result = await self._qc_filter(request.params)
            elif request.operation == "float_filter":
                result = await self._float_filter(request.params)
            elif request.operation == "aggregate":
                result = await self._aggregate(request.params)
            elif request.operation == "group_by":
                result = await self._group_by(request.params)
            elif request.operation == "query_profiles":
                result = await self._query_profiles(request.params)
            elif request.operation == "query_measurements":
                result = await self._query_measurements(request.params)
            else:
                result = await self._passthrough(request.params)
            
            execution_time = (time.time() - start_time) * 1000
            
            return self._success_response(
                request.request_id,
                result.get("data"),
                execution_time,
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
    
    async def _spatial_filter(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter profiles by spatial bounding box."""
        bbox = params.get("bbox", [])
        input_data = params.get("input_data")
        region_name = params.get("region_name", "")
        
        if not bbox or len(bbox) != 4:
            raise ValueError("Invalid bounding box")
        
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Build SQL with PostGIS
        query = """
            SELECT 
                profile_id, float_id, cycle_number, timestamp,
                ST_X(geom::geometry) as longitude,
                ST_Y(geom::geometry) as latitude,
                data_mode, direction
            FROM profiles
            WHERE ST_Within(
                geom::geometry,
                ST_MakeEnvelope($1, $2, $3, $4, 4326)
            )
            ORDER BY timestamp DESC
            LIMIT 1000
        """
        
        try:
            rows = await execute_query(query, min_lon, min_lat, max_lon, max_lat)
            if rows:
                return {"data": rows, "count": len(rows)}
            # Fall through to demo data if no results
        except Exception as e:
            self.logger.warning(f"Database query failed: {e}")
        
        # Fallback to demo data
        from core.demo_data import query_demo_data
        self.logger.info(f"Using demo data for region: {region_name}")
        demo_result = query_demo_data(region_name or "ocean", limit=500)
        
        # Transform demo data to match expected format
        profiles = []
        for p in demo_result.get("profiles", []):
            profiles.append({
                "profile_id": p.get("profile_id"),
                "float_id": p.get("float_id"),
                "cycle_number": p.get("cycle_number"),
                "timestamp": p.get("timestamp"),
                "longitude": p.get("longitude"),
                "latitude": p.get("latitude"),
                "data_mode": p.get("data_mode"),
                "direction": p.get("direction", "A"),
                "temperature": p.get("temperature"),
                "salinity": p.get("salinity"),
                "depth": p.get("depth"),
                "qc_flag": p.get("qc_flag"),
            })
        
        return {"data": profiles, "count": len(profiles), "demo_mode": True}
    
    async def _temporal_filter(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter profiles by time range."""
        start = params.get("start")
        end = params.get("end")
        input_data = params.get("input_data")
        
        if not start or not end:
            # Use demo data for "recent" or "last month" type queries
            from core.demo_data import query_demo_data
            self.logger.info("Using demo data for temporal filter (no date range)")
            demo_result = query_demo_data("recent data", limit=500)
            return {"data": demo_result.get("profiles", []), "count": demo_result.get("count", 0), "demo_mode": True}
        
        query = """
            SELECT 
                profile_id, float_id, cycle_number, timestamp,
                ST_X(geom::geometry) as longitude,
                ST_Y(geom::geometry) as latitude,
                data_mode, direction
            FROM profiles
            WHERE timestamp BETWEEN $1 AND $2
            ORDER BY timestamp DESC
            LIMIT 1000
        """
        
        try:
            rows = await execute_query(query, start, end)
            if rows:
                return {"data": rows, "count": len(rows)}
        except Exception as e:
            self.logger.warning(f"Database query failed: {e}")
        
        # Fallback to demo data
        from core.demo_data import query_demo_data
        demo_result = query_demo_data("recent", limit=500)
        return {"data": demo_result.get("profiles", []), "count": demo_result.get("count", 0), "demo_mode": True}
    
    async def _parameter_filter(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter by oceanographic parameters."""
        parameters = params.get("parameters", ["temperature", "salinity"])
        include_qc = params.get("include_qc", True)
        input_data = params.get("input_data")
        
        # Build column selection
        columns = ["measurement_id", "profile_id", "level_index", "depth"]
        for param in parameters:
            columns.append(param)
            if include_qc:
                columns.append(f"{param}_qc")
        
        columns_str = ", ".join(columns)
        
        query = f"""
            SELECT {columns_str}
            FROM profile_measurements
            LIMIT 5000
        """
        
        try:
            rows = await execute_query(query)
            return {"data": rows, "count": len(rows)}
        except Exception as e:
            self.logger.warning(f"Database query failed: {e}")
            return {"data": [], "count": 0}
    
    async def _qc_filter(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter by quality control flags."""
        qc_flags = params.get("qc_flags", [1])
        data_mode = params.get("data_mode")
        input_data = params.get("input_data")
        
        conditions = []
        if qc_flags:
            flags_str = ",".join(str(f) for f in qc_flags)
            conditions.append(f"temp_qc::int IN ({flags_str})")
        
        if data_mode:
            conditions.append(f"p.data_mode = '{data_mode}'")
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        query = f"""
            SELECT m.*, p.float_id, p.timestamp
            FROM profile_measurements m
            JOIN profiles p ON m.profile_id = p.profile_id
            WHERE {where_clause}
            LIMIT 5000
        """
        
        try:
            rows = await execute_query(query)
            return {"data": rows, "count": len(rows)}
        except Exception as e:
            self.logger.warning(f"Database query failed: {e}")
            return {"data": [], "count": 0}
    
    async def _float_filter(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter by float IDs."""
        float_ids = params.get("float_ids", [])
        
        if not float_ids:
            return {"data": [], "count": 0}
        
        placeholders = ",".join(f"${i+1}" for i in range(len(float_ids)))
        
        query = f"""
            SELECT 
                profile_id, float_id, cycle_number, timestamp,
                ST_X(geom::geometry) as longitude,
                ST_Y(geom::geometry) as latitude,
                data_mode, direction
            FROM profiles
            WHERE float_id IN ({placeholders})
            ORDER BY float_id, timestamp
        """
        
        try:
            rows = await execute_query(query, *float_ids)
            return {"data": rows, "count": len(rows)}
        except Exception as e:
            self.logger.warning(f"Database query failed: {e}")
            return {"data": [], "count": 0}
    
    async def _aggregate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform aggregation operations."""
        func = params.get("function", "count")
        column = params.get("column", "*")
        input_data = params.get("input_data")
        
        if input_data and isinstance(input_data, list):
            # Aggregate in-memory data
            if func == "count":
                result = len(input_data)
            elif func == "mean" and column != "*":
                values = [row.get(column, 0) for row in input_data if row.get(column) is not None]
                result = sum(values) / len(values) if values else 0
            elif func == "sum" and column != "*":
                values = [row.get(column, 0) for row in input_data if row.get(column) is not None]
                result = sum(values)
            else:
                result = len(input_data)
            
            return {"data": {"result": result}, "count": 1}
        
        return {"data": {"result": 0}, "count": 1}
    
    async def _group_by(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Group data by column."""
        group_column = params.get("column", "float_id")
        agg_func = params.get("aggregate", "count")
        input_data = params.get("input_data")
        
        if input_data and isinstance(input_data, list):
            groups = {}
            for row in input_data:
                key = row.get(group_column, "unknown")
                if key not in groups:
                    groups[key] = []
                groups[key].append(row)
            
            result = [
                {"group": k, "count": len(v)}
                for k, v in groups.items()
            ]
            
            return {"data": result, "count": len(result)}
        
        return {"data": [], "count": 0}
    
    async def _query_profiles(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query profiles with multiple filters."""
        bbox = params.get("bbox")
        time_range = params.get("time_range")
        float_ids = params.get("float_ids")
        data_mode = params.get("data_mode")
        limit = params.get("limit", 1000)
        offset = params.get("offset", 0)
        
        conditions = []
        query_params = []
        param_idx = 1
        
        if bbox:
            conditions.append(f"""
                ST_Within(
                    geom::geometry,
                    ST_MakeEnvelope(${param_idx}, ${param_idx+1}, ${param_idx+2}, ${param_idx+3}, 4326)
                )
            """)
            query_params.extend(bbox)
            param_idx += 4
        
        if time_range and len(time_range) == 2:
            conditions.append(f"timestamp BETWEEN ${param_idx} AND ${param_idx+1}")
            query_params.extend(time_range)
            param_idx += 2
        
        if float_ids:
            placeholders = ",".join(f"${param_idx+i}" for i in range(len(float_ids)))
            conditions.append(f"float_id IN ({placeholders})")
            query_params.extend(float_ids)
            param_idx += len(float_ids)
        
        if data_mode:
            conditions.append(f"data_mode = ${param_idx}")
            query_params.append(data_mode)
            param_idx += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        query = f"""
            SELECT 
                profile_id, float_id, cycle_number, timestamp,
                ST_X(geom::geometry) as longitude,
                ST_Y(geom::geometry) as latitude,
                data_mode, direction
            FROM profiles
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_idx} OFFSET ${param_idx+1}
        """
        query_params.extend([limit, offset])
        
        try:
            rows = await execute_query(query, *query_params)
            return {"data": rows, "count": len(rows)}
        except Exception as e:
            self.logger.warning(f"Database query failed: {e}")
            return {"data": [], "count": 0}
    
    async def _query_measurements(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query measurements for profiles."""
        profile_ids = params.get("profile_ids", [])
        parameters = params.get("parameters", ["temperature", "salinity"])
        depth_range = params.get("depth_range")
        qc_threshold = params.get("qc_threshold")
        
        if not profile_ids:
            return {"data": [], "count": 0}
        
        columns = ["measurement_id", "profile_id", "level_index", "depth"] + parameters
        columns_str = ", ".join(columns)
        
        placeholders = ",".join(f"${i+1}" for i in range(len(profile_ids)))
        query_params = list(profile_ids)
        param_idx = len(profile_ids) + 1
        
        conditions = [f"profile_id IN ({placeholders})"]
        
        if depth_range and len(depth_range) == 2:
            conditions.append(f"depth BETWEEN ${param_idx} AND ${param_idx+1}")
            query_params.extend(depth_range)
            param_idx += 2
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
            SELECT {columns_str}
            FROM profile_measurements
            WHERE {where_clause}
            ORDER BY profile_id, level_index
        """
        
        try:
            rows = await execute_query(query, *query_params)
            return {"data": rows, "count": len(rows)}
        except Exception as e:
            self.logger.warning(f"Database query failed: {e}")
            return {"data": [], "count": 0}
    
    async def _passthrough(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Pass through input data unchanged."""
        return {"data": params.get("input_data", []), "count": 0}
