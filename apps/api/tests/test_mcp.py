"""
Tests for MCP servers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from mcp import (
    MCPOrchestrator,
    StructuredServer,
    MetadataServer,
    ProfileServer,
    SemanticServer,
    CachingServer,
    VisualizationServer
)
from mcp.base import MCPRequest, MCPResponse
from models.operators import OperatorType, ExecutionPlan, ExecutionStep


class TestStructuredServer:
    """Tests for Structured MCP Server (SQL/PostGIS)."""
    
    @pytest.fixture
    def server(self):
        server = StructuredServer()
        # Mock database connection
        server.pool = MagicMock()
        return server
        
    @pytest.mark.asyncio
    async def test_spatial_filter(self, server):
        """Should execute spatial filter query."""
        request = MCPRequest(
            operator_type=OperatorType.SPATIAL_FILTER,
            config={
                "bounds": {
                    "lat": [5, 25],
                    "lon": [50, 80]
                }
            }
        )
        
        # Mock database response
        server.pool.acquire.return_value.__aenter__.return_value.fetch = AsyncMock(
            return_value=[
                {"float_id": "6901234", "lat": 15.0, "lon": 65.0},
                {"float_id": "6901235", "lat": 20.0, "lon": 70.0}
            ]
        )
        
        response = await server.execute(request)
        
        assert isinstance(response, MCPResponse)
        assert response.success
        
    @pytest.mark.asyncio
    async def test_temporal_filter(self, server):
        """Should execute temporal filter query."""
        request = MCPRequest(
            operator_type=OperatorType.TEMPORAL_FILTER,
            config={
                "range": "last_month"
            }
        )
        
        server.pool.acquire.return_value.__aenter__.return_value.fetch = AsyncMock(
            return_value=[]
        )
        
        response = await server.execute(request)
        
        assert response.success
        

class TestProfileServer:
    """Tests for Profile MCP Server (computations)."""
    
    @pytest.fixture
    def server(self):
        return ProfileServer()
        
    @pytest.mark.asyncio
    async def test_compute_mld(self, server):
        """Should compute mixed layer depth."""
        request = MCPRequest(
            operator_type=OperatorType.COMPUTE_MLD,
            config={
                "method": "threshold",
                "threshold": 0.2
            },
            input_data={
                "profiles": [
                    {
                        "float_id": "6901234",
                        "pressure": [5, 10, 20, 50, 100, 200, 500],
                        "temperature": [28, 28, 27.9, 25, 18, 12, 6],
                        "salinity": [35, 35, 35, 35.1, 35.2, 35.3, 35.4]
                    }
                ]
            }
        )
        
        response = await server.execute(request)
        
        assert response.success
        assert "mld" in response.data or "mixed_layer_depth" in response.data
        
    @pytest.mark.asyncio
    async def test_compute_gradient(self, server):
        """Should compute vertical gradient."""
        request = MCPRequest(
            operator_type=OperatorType.COMPUTE_GRADIENT,
            config={
                "parameter": "temperature"
            },
            input_data={
                "profiles": [
                    {
                        "pressure": [10, 20, 50, 100],
                        "temperature": [28, 27, 22, 15]
                    }
                ]
            }
        )
        
        response = await server.execute(request)
        
        assert response.success
        assert "gradient" in response.data
        
    @pytest.mark.asyncio
    async def test_compute_statistics(self, server):
        """Should compute basic statistics."""
        request = MCPRequest(
            operator_type=OperatorType.COMPUTE_STATISTICS,
            config={
                "parameters": ["temperature", "salinity"]
            },
            input_data={
                "values": {
                    "temperature": [25, 26, 27, 28, 25.5],
                    "salinity": [35, 35.1, 35.2, 35.0, 35.05]
                }
            }
        )
        
        response = await server.execute(request)
        
        assert response.success
        assert "temperature" in response.data
        assert "mean" in response.data["temperature"]
        assert "std" in response.data["temperature"]


class TestSemanticServer:
    """Tests for Semantic MCP Server (vector search)."""
    
    @pytest.fixture
    def server(self):
        server = SemanticServer()
        # Mock ChromaDB client
        server.client = MagicMock()
        return server
        
    @pytest.mark.asyncio
    async def test_semantic_search(self, server):
        """Should perform semantic search."""
        # Mock collection
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2"]],
            "documents": [["Profile in Arabian Sea", "Profile in Bay of Bengal"]],
            "metadatas": [[{"float_id": "123"}, {"float_id": "456"}]],
            "distances": [[0.1, 0.2]]
        }
        server.client.get_collection.return_value = mock_collection
        
        request = MCPRequest(
            operator_type=OperatorType.SEMANTIC_SEARCH,
            config={
                "query": "warm water profiles in monsoon season",
                "n_results": 10
            }
        )
        
        response = await server.execute(request)
        
        assert response.success
        assert len(response.data.get("results", [])) > 0


class TestVisualizationServer:
    """Tests for Visualization MCP Server."""
    
    @pytest.fixture
    def server(self):
        return VisualizationServer()
        
    @pytest.mark.asyncio
    async def test_generate_trajectory_map(self, server):
        """Should generate trajectory map spec."""
        request = MCPRequest(
            operator_type=OperatorType.VISUALIZATION,
            config={
                "viz_type": "trajectory_map"
            },
            input_data={
                "trajectories": [
                    {
                        "float_id": "6901234",
                        "positions": [
                            {"lat": 15.0, "lon": 65.0, "timestamp": "2024-01-01"},
                            {"lat": 15.5, "lon": 65.5, "timestamp": "2024-01-11"}
                        ]
                    }
                ]
            }
        )
        
        response = await server.execute(request)
        
        assert response.success
        assert response.visualization is not None
        assert response.visualization.type == "trajectory_map"
        assert response.visualization.library == "leaflet"
        
    @pytest.mark.asyncio
    async def test_generate_vertical_profile(self, server):
        """Should generate vertical profile spec."""
        request = MCPRequest(
            operator_type=OperatorType.VISUALIZATION,
            config={
                "viz_type": "vertical_profile"
            },
            input_data={
                "profiles": [
                    {
                        "pressure": [10, 50, 100, 200, 500],
                        "temperature": [28, 26, 20, 15, 8],
                        "salinity": [35, 35.1, 35.2, 35.3, 35.4]
                    }
                ]
            }
        )
        
        response = await server.execute(request)
        
        assert response.success
        assert response.visualization is not None
        
    @pytest.mark.asyncio
    async def test_generate_ts_diagram(self, server):
        """Should generate T-S diagram spec."""
        request = MCPRequest(
            operator_type=OperatorType.VISUALIZATION,
            config={
                "viz_type": "ts_diagram"
            },
            input_data={
                "points": [
                    {"temperature": 28, "salinity": 35, "pressure": 10},
                    {"temperature": 20, "salinity": 35.2, "pressure": 100}
                ]
            }
        )
        
        response = await server.execute(request)
        
        assert response.success


class TestMCPOrchestrator:
    """Tests for MCP Orchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        orch = MCPOrchestrator()
        # Mock all servers
        orch.servers = {
            "structured": MagicMock(),
            "metadata": MagicMock(),
            "profile": MagicMock(),
            "semantic": MagicMock(),
            "caching": MagicMock(),
            "visualization": MagicMock()
        }
        return orch
        
    @pytest.mark.asyncio
    async def test_execute_single_step(self, orchestrator):
        """Should execute single step plan."""
        plan = ExecutionPlan(
            steps=[
                ExecutionStep(
                    operator_id="spatial",
                    operator_type=OperatorType.SPATIAL_FILTER,
                    server="structured",
                    config={"bounds": {"lat": [5, 25], "lon": [50, 80]}},
                    estimated_cost_ms=100
                )
            ],
            estimated_cost=100,
            parallel_groups=[["spatial"]]
        )
        
        # Mock server response
        orchestrator.servers["structured"].execute = AsyncMock(
            return_value=MCPResponse(
                success=True,
                data={"profiles": []}
            )
        )
        
        result = await orchestrator.execute(plan)
        
        assert result.success
        orchestrator.servers["structured"].execute.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_execute_parallel_steps(self, orchestrator):
        """Should execute independent steps in parallel."""
        plan = ExecutionPlan(
            steps=[
                ExecutionStep(
                    operator_id="spatial",
                    operator_type=OperatorType.SPATIAL_FILTER,
                    server="structured",
                    config={},
                    estimated_cost_ms=100
                ),
                ExecutionStep(
                    operator_id="temporal",
                    operator_type=OperatorType.TEMPORAL_FILTER,
                    server="structured",
                    config={},
                    estimated_cost_ms=100
                )
            ],
            estimated_cost=100,  # Parallel so not 200
            parallel_groups=[["spatial", "temporal"]]
        )
        
        orchestrator.servers["structured"].execute = AsyncMock(
            return_value=MCPResponse(success=True, data={})
        )
        
        result = await orchestrator.execute(plan)
        
        assert result.success
        # Both should be called
        assert orchestrator.servers["structured"].execute.call_count == 2
        
    @pytest.mark.asyncio
    async def test_data_flow_between_steps(self, orchestrator):
        """Should pass data between dependent steps."""
        plan = ExecutionPlan(
            steps=[
                ExecutionStep(
                    operator_id="retrieve",
                    operator_type=OperatorType.PROFILE_RETRIEVAL,
                    server="structured",
                    config={},
                    estimated_cost_ms=100,
                    dependencies=[]
                ),
                ExecutionStep(
                    operator_id="compute",
                    operator_type=OperatorType.COMPUTE_MLD,
                    server="profile",
                    config={},
                    estimated_cost_ms=50,
                    dependencies=["retrieve"]
                )
            ],
            estimated_cost=150,
            parallel_groups=[["retrieve"], ["compute"]]
        )
        
        # First step returns profiles
        orchestrator.servers["structured"].execute = AsyncMock(
            return_value=MCPResponse(
                success=True,
                data={"profiles": [{"pressure": [10, 50, 100], "temperature": [28, 25, 18]}]}
            )
        )
        
        # Second step uses profiles
        orchestrator.servers["profile"].execute = AsyncMock(
            return_value=MCPResponse(
                success=True,
                data={"mld": [45]}
            )
        )
        
        result = await orchestrator.execute(plan)
        
        assert result.success
        
        # Verify data was passed to second call
        second_call = orchestrator.servers["profile"].execute.call_args
        assert second_call is not None
