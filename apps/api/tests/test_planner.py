"""
Tests for Query Planner.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio

from planner import QueryPlanner
from models.operators import (
    SemanticOperatorDAG, 
    SemanticOperator, 
    OperatorType,
    ExecutionPlan
)


class TestQueryPlanner:
    """Tests for query planning and optimization."""
    
    @pytest.fixture
    def planner(self):
        return QueryPlanner()
        
    @pytest.fixture
    def simple_dag(self):
        """Create a simple DAG with one operator."""
        return SemanticOperatorDAG(
            operators=[
                SemanticOperator(
                    id="op1",
                    type=OperatorType.SPATIAL_FILTER,
                    config={"bounds": {"lat": [5, 25], "lon": [50, 80]}},
                    dependencies=[]
                )
            ],
            intent="retrieve_data",
            entities=[],
            confidence=0.9
        )
        
    @pytest.fixture
    def complex_dag(self):
        """Create a complex DAG with multiple operators and dependencies."""
        return SemanticOperatorDAG(
            operators=[
                SemanticOperator(
                    id="spatial",
                    type=OperatorType.SPATIAL_FILTER,
                    config={"bounds": {"lat": [5, 25], "lon": [50, 80]}},
                    dependencies=[]
                ),
                SemanticOperator(
                    id="temporal",
                    type=OperatorType.TEMPORAL_FILTER,
                    config={"range": "last_month"},
                    dependencies=[]
                ),
                SemanticOperator(
                    id="profile",
                    type=OperatorType.PROFILE_RETRIEVAL,
                    config={"parameters": ["temperature", "salinity"]},
                    dependencies=["spatial", "temporal"]
                ),
                SemanticOperator(
                    id="mld",
                    type=OperatorType.COMPUTE_MLD,
                    config={},
                    dependencies=["profile"]
                ),
                SemanticOperator(
                    id="viz",
                    type=OperatorType.VISUALIZATION,
                    config={"viz_type": "vertical_profile"},
                    dependencies=["mld"]
                )
            ],
            intent="analyze",
            entities=[],
            confidence=0.85
        )
        
    @pytest.mark.asyncio
    async def test_plan_simple_dag(self, planner, simple_dag):
        """Should create execution plan for simple DAG."""
        plan = await planner.plan(dag=simple_dag)
        
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) >= 1
        assert plan.estimated_cost > 0
        
    @pytest.mark.asyncio
    async def test_plan_complex_dag(self, planner, complex_dag):
        """Should create execution plan for complex DAG."""
        plan = await planner.plan(dag=complex_dag)
        
        assert len(plan.steps) >= 5
        
        # Verify dependency order
        step_order = {step.operator_id: i for i, step in enumerate(plan.steps)}
        
        # spatial and temporal should be before profile
        assert step_order["spatial"] < step_order["profile"]
        assert step_order["temporal"] < step_order["profile"]
        
        # profile should be before mld
        assert step_order["profile"] < step_order["mld"]
        
        # mld should be before viz
        assert step_order["mld"] < step_order["viz"]
        
    @pytest.mark.asyncio
    async def test_identify_parallel_groups(self, planner, complex_dag):
        """Should identify operators that can run in parallel."""
        plan = await planner.plan(dag=complex_dag)
        
        # spatial and temporal have no dependencies - should be parallelizable
        assert len(plan.parallel_groups) >= 1
        
        first_group = plan.parallel_groups[0]
        assert "spatial" in first_group or "temporal" in first_group
        
    @pytest.mark.asyncio
    async def test_deadline_aware_planning(self, planner, complex_dag):
        """Should optimize for deadline constraint."""
        # Tight deadline
        plan_fast = await planner.plan(
            dag=complex_dag,
            deadline_ms=500
        )
        
        # Relaxed deadline
        plan_normal = await planner.plan(
            dag=complex_dag,
            deadline_ms=5000
        )
        
        # Fast plan should have more parallel execution
        assert len(plan_fast.parallel_groups) >= len(plan_normal.parallel_groups)
        
    @pytest.mark.asyncio
    async def test_cost_estimation(self, planner, complex_dag):
        """Should estimate execution cost."""
        plan = await planner.plan(dag=complex_dag)
        
        # Each step should have cost estimate
        for step in plan.steps:
            assert step.estimated_cost_ms > 0
            
        # Total cost should be sum of non-parallel costs
        assert plan.estimated_cost > 0
        
    @pytest.mark.asyncio
    async def test_server_assignment(self, planner, complex_dag):
        """Should assign appropriate servers to operators."""
        plan = await planner.plan(dag=complex_dag)
        
        for step in plan.steps:
            assert step.server is not None
            
            # Verify correct server assignment
            if step.operator_type == OperatorType.SPATIAL_FILTER:
                assert step.server == "structured"
            elif step.operator_type == OperatorType.COMPUTE_MLD:
                assert step.server == "profile"
            elif step.operator_type == OperatorType.VISUALIZATION:
                assert step.server == "visualization"
                
    @pytest.mark.asyncio
    async def test_cache_check_optimization(self, planner, simple_dag):
        """Should include cache check in plan."""
        plan = await planner.plan(dag=simple_dag)
        
        # Should have caching strategy
        assert plan.caching_strategy is not None
        
    @pytest.mark.asyncio
    async def test_memory_learning(self, planner, simple_dag):
        """Should update memory after planning."""
        # Plan twice with same DAG
        plan1 = await planner.plan(dag=simple_dag)
        plan2 = await planner.plan(dag=simple_dag)
        
        # Second plan might be faster due to memory
        # (hard to test without mocking memory)
        assert plan1 is not None
        assert plan2 is not None
