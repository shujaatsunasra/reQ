"""
MCP Orchestrator - Coordinates execution across MCP servers.
"""

import asyncio
from typing import List, Dict, Any, Optional
import time

from core.logging import get_logger
from models.operators import ExecutionPlan, ExecutionStep
from models.responses import ExecutionResult, VisualizationSpec
from .base import MCPRequest, MCPResponse
from .structured_server import StructuredDataServer
from .metadata_server import MetadataProcessingServer
from .profile_server import ProfileAnalysisServer
from .semantic_server import SemanticDataServer
from .caching_server import CachingServer
from .visualization_server import VisualizationServer

logger = get_logger(__name__)


class MCPOrchestrator:
    """
    Orchestrates execution across multiple MCP servers.
    
    Handles:
    - Server routing based on execution plan
    - Parallel execution of independent steps
    - Result aggregation
    - Error handling and retries
    """
    
    def __init__(self):
        # Initialize all MCP servers
        self.servers = {
            "structured": StructuredDataServer(),
            "metadata": MetadataProcessingServer(),
            "profile": ProfileAnalysisServer(),
            "semantic": SemanticDataServer(),
            "cache": CachingServer(),
            "visualization": VisualizationServer()
        }
    
    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """
        Execute a query plan across MCP servers.
        
        Args:
            plan: The execution plan to run
        
        Returns:
            ExecutionResult with aggregated data
        """
        start_time = time.time()
        logger.info(f"Executing plan {plan.plan_id} with {len(plan.steps)} steps")
        
        # Track results from each step
        step_results: Dict[str, Any] = {}
        cache_hits = 0
        total_rows = 0
        errors = []
        
        # Execute steps in parallel groups
        for group_indices in plan.parallel_groups:
            # Get steps for this group
            group_steps = [plan.steps[i] for i in group_indices]
            
            # Execute in parallel
            tasks = [
                self._execute_step(step, step_results)
                for step in group_steps
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                step = group_steps[i]
                
                if isinstance(result, Exception):
                    errors.append({
                        "step": step.operator.id,
                        "error": str(result)
                    })
                    logger.error(f"Step {step.operator.id} failed: {result}")
                else:
                    step_results[step.operator.id] = result
                    
                    if result.get("from_cache"):
                        cache_hits += 1
                    if result.get("rows_count"):
                        total_rows += result["rows_count"]
        
        # Aggregate final result
        execution_time = (time.time() - start_time) * 1000
        
        # Collect all data from steps (prioritize profile data)
        final_data = None
        profiles_data = None
        
        if plan.steps:
            # Look for profile/spatial data first (usually first step)
            for step in plan.steps:
                step_id = step.operator.id
                step_data = step_results.get(step_id, {}).get("data")
                
                if step_data:
                    # Check if this is profile data (list or has profiles key)
                    if isinstance(step_data, list) and len(step_data) > 0:
                        profiles_data = step_data
                    elif isinstance(step_data, dict) and "profiles" in step_data:
                        profiles_data = step_data.get("profiles")
                    elif isinstance(step_data, dict) and step_data.get("data"):
                        profiles_data = step_data.get("data")
            
            # Get last step data (usually visualization)
            last_step_id = plan.steps[-1].operator.id
            last_data = step_results.get(last_step_id, {}).get("data")
            
            # Combine profile data with final visualization data
            if profiles_data:
                final_data = {
                    "profiles": profiles_data,
                    "count": len(profiles_data) if isinstance(profiles_data, list) else 0,
                }
                if isinstance(last_data, dict):
                    final_data.update(last_data)
            else:
                final_data = last_data
        
        # Calculate confidence based on execution success
        confidence = 1.0 - (len(errors) / len(plan.steps)) if plan.steps else 0.0
        
        return ExecutionResult(
            success=len(errors) == 0,
            data=final_data,
            confidence=confidence,
            cache_hits=cache_hits,
            rows_processed=total_rows,
            execution_time_ms=execution_time,
            errors=errors if errors else None
        )
    
    async def _execute_step(
        self,
        step: ExecutionStep,
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single step with the appropriate MCP server."""
        server = self.servers.get(step.mcp_server)
        
        if not server:
            raise ValueError(f"Unknown MCP server: {step.mcp_server}")
        
        # Build request with data from dependencies
        params = step.operator.params.copy()
        
        # Inject data from dependent steps
        for dep_id in step.depends_on:
            if dep_id in previous_results:
                params["input_data"] = previous_results[dep_id].get("data")
        
        # Handle type as either enum or string (due to use_enum_values=True in Pydantic)
        op_type = step.operator.type
        op_type_str = op_type.value if hasattr(op_type, 'value') else str(op_type)
        
        request = MCPRequest(
            operation=op_type_str,
            params=params,
            timeout=step.timeout
        )
        
        # Execute with timeout
        try:
            response = await asyncio.wait_for(
                server.execute(request),
                timeout=step.timeout / 1000
            )
            
            if response.success:
                return {
                    "data": response.data,
                    "rows_count": response.metadata.get("rows_count", 0) if response.metadata else 0,
                    "from_cache": response.metadata.get("from_cache", False) if response.metadata else False
                }
            else:
                raise Exception(response.error.get("message", "Unknown error"))
                
        except asyncio.TimeoutError:
            raise Exception(f"Step timed out after {step.timeout}ms")
    
    async def generate_visualizations(
        self,
        data: Dict[str, Any],
        query_intent: str
    ) -> List[VisualizationSpec]:
        """
        Generate visualizations for query results.
        
        Args:
            data: Query result data
            query_intent: The detected query intent
        
        Returns:
            List of visualization specifications
        """
        viz_server = self.servers["visualization"]
        visualizations = []
        
        if not data:
            return visualizations
        
        # Determine visualization types based on intent
        viz_types = self._get_viz_types_for_intent(query_intent)
        
        for viz_type in viz_types[:2]:  # Generate up to 2 visualizations
            request = MCPRequest(
                operation="generate",
                params={
                    "type": viz_type,
                    "data": data,
                    "options": {}
                }
            )
            
            response = await viz_server.execute(request)
            
            if response.success and response.data:
                visualizations.append(VisualizationSpec(
                    type=viz_type,
                    library=response.data.get("library", "plotly"),
                    spec=response.data.get("spec", {}),
                    title=response.data.get("title"),
                    description=response.data.get("description")
                ))
        
        return visualizations
    
    def _get_viz_types_for_intent(self, intent: str) -> List[str]:
        """Map query intent to visualization types."""
        mapping = {
            "trajectory_tracking": ["trajectory_map", "time_series"],
            "profile_analysis": ["vertical_profile", "hovmoller"],
            "time_series_analysis": ["time_series", "hovmoller"],
            "spatial_analysis": ["heatmap", "trajectory_map"],
            "anomaly_detection": ["heatmap", "time_series"],
            "comparison": ["vertical_profile", "time_series"],
            "float_tracking": ["trajectory_map", "time_series"],
            "gradient_analysis": ["heatmap", "vertical_profile"],
            "water_mass_analysis": ["ts_diagram"],
            "mixed_layer_analysis": ["hovmoller", "time_series"],
            "quality_check": ["qc_dashboard"],
            "general_query": ["time_series", "vertical_profile"]
        }
        
        return mapping.get(intent, ["time_series"])
