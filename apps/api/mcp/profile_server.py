"""
ProfileAnalysisServer - Handles oceanographic computations.
"""

from typing import List, Dict, Any, Optional
import time
import math

from core.logging import get_logger
from .base import MCPServer, MCPRequest, MCPResponse

logger = get_logger(__name__)


class ProfileAnalysisServer(MCPServer):
    """
    MCP Server for profile analysis and oceanographic computations.
    
    Handles:
    - Mixed layer depth calculation
    - Gradient computation
    - Anomaly detection
    - Statistical analysis
    """
    
    def __init__(self):
        super().__init__("profile")
    
    def get_operations(self) -> List[str]:
        return [
            "compute_gradient",
            "compute_mld",
            "compute_anomaly",
            "compute_stats"
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
            if request.operation == "compute_gradient":
                result = await self._compute_gradient(request.params)
            elif request.operation == "compute_mld":
                result = await self._compute_mld(request.params)
            elif request.operation == "compute_anomaly":
                result = await self._compute_anomaly(request.params)
            elif request.operation == "compute_stats":
                result = await self._compute_stats(request.params)
            else:
                result = {"data": None, "count": 0}
            
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
    
    async def _compute_gradient(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute vertical gradient of a parameter.
        
        Uses finite difference or spline-based methods.
        """
        input_data = params.get("input_data", [])
        parameter = params.get("parameter", "temperature")
        method = params.get("method", "finite_difference")
        fast_mode = params.get("fast_mode", False)
        
        if not input_data:
            return {"data": [], "count": 0}
        
        # Group by profile
        profiles = {}
        for row in input_data:
            pid = row.get("profile_id")
            if pid not in profiles:
                profiles[pid] = []
            profiles[pid].append(row)
        
        results = []
        
        for pid, measurements in profiles.items():
            # Sort by depth
            measurements.sort(key=lambda x: x.get("depth", 0))
            
            # Compute gradients
            for i in range(1, len(measurements)):
                depth1 = measurements[i-1].get("depth", 0)
                depth2 = measurements[i].get("depth", 0)
                val1 = measurements[i-1].get(parameter)
                val2 = measurements[i].get(parameter)
                
                if val1 is not None and val2 is not None and depth2 != depth1:
                    gradient = (val2 - val1) / (depth2 - depth1)
                    
                    results.append({
                        "profile_id": pid,
                        "depth": (depth1 + depth2) / 2,
                        f"{parameter}_gradient": gradient
                    })
            
            # Skip every other profile in fast mode
            if fast_mode and len(results) > 100:
                break
        
        return {"data": results, "count": len(results)}
    
    async def _compute_mld(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute mixed layer depth.
        
        Methods:
        - temperature_threshold: MLD where temp differs from surface by threshold
        - density_threshold: MLD where density differs from surface by threshold
        """
        input_data = params.get("input_data", [])
        method = params.get("method", "temperature_threshold")
        threshold = params.get("threshold", 0.5)  # °C for temperature
        fast_mode = params.get("fast_mode", False)
        
        if not input_data:
            return {"data": [], "count": 0}
        
        # Group by profile
        profiles = {}
        for row in input_data:
            pid = row.get("profile_id")
            if pid not in profiles:
                profiles[pid] = []
            profiles[pid].append(row)
        
        results = []
        
        for pid, measurements in profiles.items():
            # Sort by depth
            measurements.sort(key=lambda x: x.get("depth", 0))
            
            if not measurements:
                continue
            
            # Get surface value (shallowest measurement)
            surface_temp = measurements[0].get("temperature")
            if surface_temp is None:
                continue
            
            # Find MLD
            mld = None
            for m in measurements:
                temp = m.get("temperature")
                if temp is not None:
                    if abs(temp - surface_temp) > threshold:
                        mld = m.get("depth")
                        break
            
            if mld is not None:
                results.append({
                    "profile_id": pid,
                    "mixed_layer_depth": mld,
                    "surface_temperature": surface_temp,
                    "method": method,
                    "threshold": threshold
                })
        
        return {"data": results, "count": len(results)}
    
    async def _compute_anomaly(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute anomalies from climatology or baseline.
        """
        input_data = params.get("input_data", [])
        parameter = params.get("parameter", "temperature")
        baseline = params.get("baseline", "mean")  # mean, climatology
        
        if not input_data:
            return {"data": [], "count": 0}
        
        # Extract parameter values
        values = [
            row.get(parameter)
            for row in input_data
            if row.get(parameter) is not None
        ]
        
        if not values:
            return {"data": [], "count": 0}
        
        # Calculate baseline
        if baseline == "mean":
            baseline_value = sum(values) / len(values)
        else:
            # Would load from climatology database
            baseline_value = sum(values) / len(values)
        
        # Calculate standard deviation
        variance = sum((v - baseline_value) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance) if variance > 0 else 1
        
        # Calculate anomalies
        results = []
        for row in input_data:
            value = row.get(parameter)
            if value is not None:
                anomaly = value - baseline_value
                z_score = anomaly / std_dev if std_dev > 0 else 0
                
                results.append({
                    **row,
                    f"{parameter}_anomaly": anomaly,
                    f"{parameter}_z_score": z_score,
                    "is_outlier": abs(z_score) > 2
                })
        
        return {"data": results, "count": len(results)}
    
    async def _compute_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute statistical summaries.
        """
        input_data = params.get("input_data", [])
        metrics = params.get("metrics", ["mean", "std", "min", "max"])
        parameters = params.get("parameters", ["temperature", "salinity"])
        
        if not input_data:
            return {"data": {}, "count": 0}
        
        results = {}
        
        for param in parameters:
            values = [
                row.get(param)
                for row in input_data
                if row.get(param) is not None
            ]
            
            if not values:
                continue
            
            param_stats = {}
            
            if "mean" in metrics:
                param_stats["mean"] = sum(values) / len(values)
            
            if "min" in metrics:
                param_stats["min"] = min(values)
            
            if "max" in metrics:
                param_stats["max"] = max(values)
            
            if "std" in metrics:
                mean = sum(values) / len(values)
                variance = sum((v - mean) ** 2 for v in values) / len(values)
                param_stats["std"] = math.sqrt(variance)
            
            if "count" in metrics:
                param_stats["count"] = len(values)
            
            if "median" in metrics:
                sorted_values = sorted(values)
                n = len(sorted_values)
                if n % 2 == 0:
                    param_stats["median"] = (sorted_values[n//2-1] + sorted_values[n//2]) / 2
                else:
                    param_stats["median"] = sorted_values[n//2]
            
            results[param] = param_stats
        
        return {"data": results, "count": len(results)}
