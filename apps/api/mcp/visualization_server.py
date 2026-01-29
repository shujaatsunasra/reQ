"""
VisualizationServer - Generates visualization specifications.
"""

from typing import List, Dict, Any, Optional, Tuple
import time

from core.logging import get_logger
from .base import MCPServer, MCPRequest, MCPResponse

logger = get_logger(__name__)


class VisualizationServer(MCPServer):
    """
    MCP Server for visualization generation.
    
    Generates specifications for:
    - Plotly charts (Hovmöller, profiles, heatmaps, T-S diagrams)
    - Leaflet maps (trajectories, spatial)
    - Recharts (time series, dashboards)
    """
    
    def __init__(self):
        super().__init__("visualization")
    
    def get_operations(self) -> List[str]:
        return [
            "generate",
            "visualize",
            "generate_trajectory_map",
            "generate_trajectory_plot",  # Scientific-style lat/lon plot
            "generate_hovmoller",
            "generate_vertical_profile",
            "generate_heatmap",
            "generate_time_series",
            "generate_qc_dashboard",
            "generate_ts_diagram"
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
            params = request.params
            viz_type = params.get("type", request.operation.replace("generate_", ""))
            
            if viz_type == "trajectory_map":
                spec, library = await self.generate_trajectory_map(
                    params.get("data", {}),
                    params.get("options"),
                    params.get("title")
                )
            elif viz_type == "trajectory_plot":
                spec, library = await self.generate_trajectory_plot(
                    params.get("data", {}),
                    params.get("options"),
                    params.get("title")
                )
            elif viz_type == "hovmoller":
                spec, library = await self.generate_hovmoller(
                    params.get("data", {}),
                    params.get("options"),
                    params.get("title")
                )
            elif viz_type == "vertical_profile":
                spec, library = await self.generate_vertical_profile(
                    params.get("data", {}),
                    params.get("options"),
                    params.get("title")
                )
            elif viz_type == "heatmap":
                spec, library = await self.generate_heatmap(
                    params.get("data", {}),
                    params.get("options"),
                    params.get("title")
                )
            elif viz_type == "time_series":
                spec, library = await self.generate_time_series(
                    params.get("data", {}),
                    params.get("options"),
                    params.get("title")
                )
            elif viz_type == "qc_dashboard":
                spec, library = await self.generate_qc_dashboard(
                    params.get("data", {}),
                    params.get("options"),
                    params.get("title")
                )
            elif viz_type == "ts_diagram":
                spec, library = await self.generate_ts_diagram(
                    params.get("data", {}),
                    params.get("options"),
                    params.get("title")
                )
            else:
                spec, library = await self.generate_time_series(
                    params.get("data", {}),
                    params.get("options"),
                    params.get("title")
                )
            
            return self._success_response(
                request.request_id,
                {"spec": spec, "library": library, "type": viz_type},
                (time.time() - start_time) * 1000
            )
            
        except Exception as e:
            self.logger.error(f"Visualization generation failed: {e}")
            return self._error_response(
                request.request_id,
                "GENERATION_ERROR",
                str(e),
                (time.time() - start_time) * 1000
            )
    
    async def generate_trajectory_map(
        self,
        data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Generate Leaflet trajectory map specification."""
        options = options or {}
        
        # Extract trajectories from data
        trajectories = []
        if isinstance(data, list):
            # Group by float_id
            floats = {}
            for point in data:
                fid = point.get("float_id", "unknown")
                if fid not in floats:
                    floats[fid] = []
                floats[fid].append({
                    "lat": point.get("latitude", 0),
                    "lng": point.get("longitude", 0),
                    "timestamp": point.get("timestamp"),
                    "cycle": point.get("cycle_number")
                })
            
            for fid, points in floats.items():
                trajectories.append({
                    "float_id": fid,
                    "points": sorted(points, key=lambda x: x.get("timestamp", ""))
                })
        
        # Calculate center and bounds
        all_points = [p for t in trajectories for p in t["points"]]
        if all_points:
            center_lat = sum(p["lat"] for p in all_points) / len(all_points)
            center_lng = sum(p["lng"] for p in all_points) / len(all_points)
        else:
            center_lat, center_lng = 0, 0
        
        spec = {
            "center": [center_lat, center_lng],
            "zoom": options.get("zoom", 4),
            "trajectories": trajectories,
            "colors": self._generate_colors(len(trajectories)),
            "markers": {
                "showStart": True,
                "showEnd": True,
                "showAll": options.get("showAllMarkers", False)
            },
            "popups": {
                "enabled": True,
                "fields": ["float_id", "timestamp", "cycle"]
            },
            "title": title or "Float Trajectories"
        }
        
        return spec, "leaflet"
    
    async def generate_trajectory_plot(
        self,
        data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Generate scientific-style trajectory plot specification.
        
        Creates a Lat vs Lon plot with:
        - Continuous line path
        - Date annotations at key points
        - Start/end markers
        - Proper axis labels
        """
        options = options or {}
        
        # Extract trajectory points
        points = []
        float_id = None
        
        if isinstance(data, list):
            for point in data:
                lat = point.get("latitude")
                lon = point.get("longitude")
                ts = point.get("timestamp") or point.get("date")
                
                if lat is not None and lon is not None:
                    points.append({
                        "latitude": lat,
                        "longitude": lon,
                        "timestamp": ts,
                        "float_id": point.get("float_id"),
                        "cycle_number": point.get("cycle_number"),
                        "temperature": point.get("temperature"),
                        "salinity": point.get("salinity"),
                    })
                    if not float_id:
                        float_id = point.get("float_id")
        
        # Sort by timestamp
        points.sort(key=lambda x: x.get("timestamp", "") or "")
        
        # Calculate milestone interval (every N points for date labels)
        marker_interval = options.get("markerInterval", max(1, len(points) // 10))
        
        spec = {
            "type": "trajectory_plot",
            "data": points,
            "floatId": float_id,
            "options": {
                "showDateLabels": options.get("showDateLabels", True),
                "showStationMarkers": options.get("showStationMarkers", True),
                "markerInterval": marker_interval,
                "height": options.get("height", 450),
            },
            "title": title or f"Float {float_id or ''} Trajectory",
            "stats": {
                "pointCount": len(points),
                "startDate": points[0]["timestamp"] if points else None,
                "endDate": points[-1]["timestamp"] if points else None,
            }
        }
        
        return spec, "recharts"
    
    async def generate_hovmoller(
        self,
        data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Generate Plotly Hovmöller diagram specification."""
        options = options or {}
        parameter = options.get("parameter", "temperature")
        
        # Extract grid data
        depths = []
        times = []
        values = []
        
        if isinstance(data, list):
            # Build depth-time grid
            depth_time_map = {}
            for row in data:
                depth = row.get("depth", 0)
                time = row.get("timestamp", "")
                value = row.get(parameter)
                
                if value is not None:
                    if depth not in depth_time_map:
                        depth_time_map[depth] = {}
                    depth_time_map[depth][time] = value
            
            depths = sorted(depth_time_map.keys())
            times = sorted(set(t for d in depth_time_map.values() for t in d.keys()))
            
            values = [
                [depth_time_map.get(d, {}).get(t, None) for t in times]
                for d in depths
            ]
        
        spec = {
            "data": [{
                "type": "contour",
                "x": times,
                "y": depths,
                "z": values,
                "colorscale": options.get("colorscale", "RdBu_r"),
                "reversescale": True,
                "contours": {
                    "coloring": "heatmap"
                },
                "colorbar": {
                    "title": parameter.capitalize()
                }
            }],
            "layout": {
                "title": title or f"Hovmöller Diagram - {parameter.capitalize()}",
                "xaxis": {"title": "Time"},
                "yaxis": {"title": "Depth (m)", "autorange": "reversed"},
                "height": options.get("height", 500),
                "width": options.get("width", 800)
            }
        }
        
        return spec, "plotly"
    
    async def generate_vertical_profile(
        self,
        data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Generate Plotly vertical profile comparison."""
        options = options or {}
        parameter = options.get("parameter", "temperature")
        
        traces = []
        
        if isinstance(data, list):
            # Group by profile
            profiles = {}
            for row in data:
                pid = row.get("profile_id", "unknown")
                if pid not in profiles:
                    profiles[pid] = {"depths": [], "values": []}
                
                depth = row.get("depth")
                value = row.get(parameter)
                
                if depth is not None and value is not None:
                    profiles[pid]["depths"].append(depth)
                    profiles[pid]["values"].append(value)
            
            colors = self._generate_colors(len(profiles))
            for i, (pid, profile) in enumerate(profiles.items()):
                traces.append({
                    "type": "scatter",
                    "x": profile["values"],
                    "y": profile["depths"],
                    "mode": "lines+markers",
                    "name": str(pid)[:16],
                    "line": {"color": colors[i]}
                })
        
        spec = {
            "data": traces,
            "layout": {
                "title": title or f"Vertical Profiles - {parameter.capitalize()}",
                "xaxis": {"title": parameter.capitalize()},
                "yaxis": {"title": "Depth (m)", "autorange": "reversed"},
                "height": options.get("height", 600),
                "width": options.get("width", 500),
                "legend": {"orientation": "h", "y": -0.15}
            }
        }
        
        return spec, "plotly"
    
    async def generate_heatmap(
        self,
        data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Generate Plotly geospatial heatmap."""
        options = options or {}
        parameter = options.get("parameter", "temperature")
        
        lats = []
        lons = []
        values = []
        
        if isinstance(data, list):
            for row in data:
                lat = row.get("latitude")
                lon = row.get("longitude")
                value = row.get(parameter)
                
                if lat is not None and lon is not None and value is not None:
                    lats.append(lat)
                    lons.append(lon)
                    values.append(value)
        
        spec = {
            "data": [{
                "type": "scattergeo",
                "lat": lats,
                "lon": lons,
                "mode": "markers",
                "marker": {
                    "size": 8,
                    "color": values,
                    "colorscale": options.get("colorscale", "Viridis"),
                    "colorbar": {"title": parameter.capitalize()}
                }
            }],
            "layout": {
                "title": title or f"Spatial Distribution - {parameter.capitalize()}",
                "geo": {
                    "projection": {"type": "natural earth"},
                    "showland": True,
                    "landcolor": "rgb(243, 243, 243)",
                    "showocean": True,
                    "oceancolor": "rgb(204, 229, 255)"
                },
                "height": options.get("height", 600),
                "width": options.get("width", 900)
            }
        }
        
        return spec, "plotly"
    
    async def generate_time_series(
        self,
        data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Generate Recharts time series specification."""
        options = options or {}
        parameters = options.get("parameters", ["temperature"])
        
        chart_data = []
        
        if isinstance(data, list):
            for row in data:
                point = {"timestamp": row.get("timestamp")}
                for param in parameters:
                    if row.get(param) is not None:
                        point[param] = row[param]
                if len(point) > 1:
                    chart_data.append(point)
        
        spec = {
            "type": "line",
            "data": chart_data,
            "xKey": "timestamp",
            "series": [
                {"dataKey": param, "name": param.capitalize()}
                for param in parameters
            ],
            "xAxis": {
                "type": "time",
                "label": "Time"
            },
            "yAxis": {
                "label": "Value"
            },
            "title": title or "Time Series",
            "legend": True,
            "tooltip": True
        }
        
        return spec, "recharts"
    
    async def generate_qc_dashboard(
        self,
        data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Generate Recharts QC dashboard specification."""
        options = options or {}
        
        # Count QC flags
        qc_counts = {1: 0, 2: 0, 3: 0, 4: 0, 8: 0, 9: 0}
        
        if isinstance(data, list):
            for row in data:
                for key in ["temp_qc", "salinity_qc", "pres_qc"]:
                    qc = row.get(key)
                    if qc is not None:
                        try:
                            qc_int = int(qc)
                            if qc_int in qc_counts:
                                qc_counts[qc_int] += 1
                        except:
                            pass
        
        qc_labels = {
            1: "Good",
            2: "Probably Good",
            3: "Questionable",
            4: "Bad",
            8: "Interpolated",
            9: "Missing"
        }
        
        pie_data = [
            {"name": qc_labels[k], "value": v, "qc_flag": k}
            for k, v in qc_counts.items()
            if v > 0
        ]
        
        bar_data = [
            {"qc_flag": str(k), "count": v, "name": qc_labels[k]}
            for k, v in qc_counts.items()
        ]
        
        spec = {
            "type": "dashboard",
            "panels": [
                {
                    "type": "pie",
                    "title": "QC Flag Distribution",
                    "data": pie_data,
                    "dataKey": "value",
                    "nameKey": "name"
                },
                {
                    "type": "bar",
                    "title": "QC Flag Counts",
                    "data": bar_data,
                    "xKey": "name",
                    "series": [{"dataKey": "count", "name": "Count"}]
                }
            ],
            "title": title or "Quality Control Dashboard"
        }
        
        return spec, "recharts"
    
    async def generate_ts_diagram(
        self,
        data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Generate Plotly T-S diagram specification."""
        options = options or {}
        
        temps = []
        sals = []
        depths = []
        
        if isinstance(data, list):
            for row in data:
                temp = row.get("temperature")
                sal = row.get("salinity")
                depth = row.get("depth", 0)
                
                if temp is not None and sal is not None:
                    temps.append(temp)
                    sals.append(sal)
                    depths.append(depth)
        
        spec = {
            "data": [{
                "type": "scatter",
                "x": sals,
                "y": temps,
                "mode": "markers",
                "marker": {
                    "size": 6,
                    "color": depths,
                    "colorscale": "Viridis",
                    "colorbar": {"title": "Depth (m)"},
                    "reversescale": True
                },
                "hovertemplate": "Salinity: %{x:.2f} PSU<br>Temperature: %{y:.2f} °C<br>Depth: %{marker.color:.0f} m"
            }],
            "layout": {
                "title": title or "T-S Diagram",
                "xaxis": {"title": "Salinity (PSU)"},
                "yaxis": {"title": "Temperature (°C)"},
                "height": options.get("height", 600),
                "width": options.get("width", 700)
            }
        }
        
        return spec, "plotly"
    
    async def generate_correlation_matrix(
        self,
        data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Generate Plotly correlation matrix."""
        options = options or {}
        parameters = options.get("parameters", ["temperature", "salinity"])
        
        # Calculate correlations (simplified)
        values = {p: [] for p in parameters}
        
        if isinstance(data, list):
            for row in data:
                for p in parameters:
                    if row.get(p) is not None:
                        values[p].append(row[p])
        
        # Build correlation matrix
        n = len(parameters)
        corr_matrix = [[1.0] * n for _ in range(n)]
        
        # Simplified correlation calculation
        for i, p1 in enumerate(parameters):
            for j, p2 in enumerate(parameters):
                if i != j:
                    v1, v2 = values[p1], values[p2]
                    if v1 and v2 and len(v1) == len(v2):
                        # Simple Pearson correlation
                        n = len(v1)
                        mean1 = sum(v1) / n
                        mean2 = sum(v2) / n
                        
                        cov = sum((v1[k] - mean1) * (v2[k] - mean2) for k in range(n)) / n
                        std1 = (sum((v - mean1) ** 2 for v in v1) / n) ** 0.5
                        std2 = (sum((v - mean2) ** 2 for v in v2) / n) ** 0.5
                        
                        if std1 > 0 and std2 > 0:
                            corr_matrix[i][j] = cov / (std1 * std2)
        
        spec = {
            "data": [{
                "type": "heatmap",
                "x": parameters,
                "y": parameters,
                "z": corr_matrix,
                "colorscale": "RdBu",
                "zmid": 0,
                "text": [[f"{v:.2f}" for v in row] for row in corr_matrix],
                "texttemplate": "%{text}",
                "colorbar": {"title": "Correlation"}
            }],
            "layout": {
                "title": title or "Parameter Correlation Matrix",
                "height": options.get("height", 500),
                "width": options.get("width", 500)
            }
        }
        
        return spec, "plotly"
    
    def _generate_colors(self, n: int) -> List[str]:
        """Generate n distinct colors for visualization."""
        colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
            "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5"
        ]
        
        # Repeat colors if needed
        while len(colors) < n:
            colors.extend(colors)
        
        return colors[:n]
