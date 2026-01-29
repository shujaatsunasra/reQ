"""
Visualization endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

from core.logging import get_logger
from mcp.visualization_server import VisualizationServer

logger = get_logger(__name__)
router = APIRouter()

viz_server = VisualizationServer()


class VisualizationType(str, Enum):
    """Supported visualization types."""
    TRAJECTORY_MAP = "trajectory_map"
    HOVMOLLER = "hovmoller"
    VERTICAL_PROFILE = "vertical_profile"
    HEATMAP = "heatmap"
    TIME_SERIES = "time_series"
    QC_DASHBOARD = "qc_dashboard"
    TS_DIAGRAM = "ts_diagram"
    CORRELATION_MATRIX = "correlation_matrix"


class VisualizationRequest(BaseModel):
    """Request model for visualization generation."""
    type: VisualizationType
    data: Dict[str, Any] = Field(..., description="Data to visualize")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Visualization options")
    title: Optional[str] = Field(default=None, description="Chart title")
    width: Optional[int] = Field(default=800, description="Chart width")
    height: Optional[int] = Field(default=600, description="Chart height")


class VisualizationResponse(BaseModel):
    """Response model for visualization generation."""
    success: bool
    type: str
    spec: Dict[str, Any]
    library: str
    render_time_ms: float


@router.post("/visualizations/generate", response_model=VisualizationResponse)
async def generate_visualization(request: VisualizationRequest) -> VisualizationResponse:
    """
    Generate a visualization specification from data.
    
    Returns a Plotly, Leaflet, or Recharts spec that can be rendered on the frontend.
    """
    import time
    start = time.time()
    
    try:
        if request.type == VisualizationType.TRAJECTORY_MAP:
            spec, library = await viz_server.generate_trajectory_map(
                data=request.data,
                options=request.options,
                title=request.title
            )
        elif request.type == VisualizationType.HOVMOLLER:
            spec, library = await viz_server.generate_hovmoller(
                data=request.data,
                options=request.options,
                title=request.title
            )
        elif request.type == VisualizationType.VERTICAL_PROFILE:
            spec, library = await viz_server.generate_vertical_profile(
                data=request.data,
                options=request.options,
                title=request.title
            )
        elif request.type == VisualizationType.HEATMAP:
            spec, library = await viz_server.generate_heatmap(
                data=request.data,
                options=request.options,
                title=request.title
            )
        elif request.type == VisualizationType.TIME_SERIES:
            spec, library = await viz_server.generate_time_series(
                data=request.data,
                options=request.options,
                title=request.title
            )
        elif request.type == VisualizationType.QC_DASHBOARD:
            spec, library = await viz_server.generate_qc_dashboard(
                data=request.data,
                options=request.options,
                title=request.title
            )
        elif request.type == VisualizationType.TS_DIAGRAM:
            spec, library = await viz_server.generate_ts_diagram(
                data=request.data,
                options=request.options,
                title=request.title
            )
        elif request.type == VisualizationType.CORRELATION_MATRIX:
            spec, library = await viz_server.generate_correlation_matrix(
                data=request.data,
                options=request.options,
                title=request.title
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown visualization type: {request.type}")
        
        render_time = (time.time() - start) * 1000
        
        return VisualizationResponse(
            success=True,
            type=request.type.value,
            spec=spec,
            library=library,
            render_time_ms=render_time
        )
    
    except Exception as e:
        logger.error(f"Visualization generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/visualizations/types")
async def get_visualization_types() -> Dict[str, Any]:
    """Get list of supported visualization types with descriptions."""
    return {
        "types": [
            {
                "id": "trajectory_map",
                "name": "Float Trajectory Map",
                "description": "Interactive map showing float paths over time",
                "library": "leaflet",
                "required_fields": ["float_id", "latitude", "longitude", "timestamp"]
            },
            {
                "id": "hovmoller",
                "name": "Hovmöller Diagram",
                "description": "Depth-time contour plot showing temporal evolution",
                "library": "plotly",
                "required_fields": ["depth", "timestamp", "parameter"]
            },
            {
                "id": "vertical_profile",
                "name": "Vertical Profile",
                "description": "Overlaid line charts comparing profiles at different depths",
                "library": "plotly",
                "required_fields": ["depth", "parameter"]
            },
            {
                "id": "heatmap",
                "name": "Geospatial Heatmap",
                "description": "Gridded interpolation of parameters over geographic area",
                "library": "plotly",
                "required_fields": ["latitude", "longitude", "parameter"]
            },
            {
                "id": "time_series",
                "name": "Time Series",
                "description": "Line chart showing parameter evolution over time",
                "library": "recharts",
                "required_fields": ["timestamp", "parameter"]
            },
            {
                "id": "qc_dashboard",
                "name": "QC Dashboard",
                "description": "Quality control statistics and flag distributions",
                "library": "recharts",
                "required_fields": ["qc_flags"]
            },
            {
                "id": "ts_diagram",
                "name": "T-S Diagram",
                "description": "Temperature-salinity scatter plot with density contours",
                "library": "plotly",
                "required_fields": ["temperature", "salinity"]
            },
            {
                "id": "correlation_matrix",
                "name": "Correlation Matrix",
                "description": "Parameter correlation heatmap",
                "library": "plotly",
                "required_fields": ["parameters"]
            }
        ]
    }
