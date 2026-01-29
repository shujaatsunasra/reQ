"""
Query Planner - Cost-based query optimization.
Generates optimized execution plans from semantic operator DAGs.
"""

import uuid
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from core.logging import get_logger
from core.redis import cache_get
from models.operators import (
    SemanticOperatorDAG,
    ExecutionPlan,
    ExecutionStep,
    Operator,
    OperatorType
)

logger = get_logger(__name__)


@dataclass
class CostEstimate:
    """Cost estimate for an operator."""
    base_cost: float
    adjusted_cost: float
    cache_available: bool
    historical_cost: Optional[float] = None


class QueryPlanner:
    """
    Cost-based query optimizer.
    
    Generates optimized execution plans that:
    1. Minimize total execution time
    2. Respect deadline constraints
    3. Maximize cache utilization
    4. Enable parallel execution where possible
    """
    
    def __init__(self):
        # Base costs for each operator type (in ms)
        self.base_costs = {
            OperatorType.SPATIAL_FILTER: 50,
            OperatorType.TEMPORAL_FILTER: 30,
            OperatorType.PARAMETER_FILTER: 20,
            OperatorType.QC_FILTER: 15,
            OperatorType.FLOAT_FILTER: 25,
            OperatorType.AGGREGATE: 100,
            OperatorType.GROUP_BY: 80,
            OperatorType.COMPUTE_GRADIENT: 150,
            OperatorType.COMPUTE_MLD: 200,
            OperatorType.COMPUTE_ANOMALY: 180,
            OperatorType.COMPUTE_STATS: 100,
            OperatorType.SEMANTIC_SEARCH: 300,
            OperatorType.JOIN: 150,
            OperatorType.VISUALIZE: 250
        }
        
        # MCP server assignments
        self.server_assignments = {
            OperatorType.SPATIAL_FILTER: "structured",
            OperatorType.TEMPORAL_FILTER: "structured",
            OperatorType.PARAMETER_FILTER: "structured",
            OperatorType.QC_FILTER: "structured",
            OperatorType.FLOAT_FILTER: "structured",
            OperatorType.AGGREGATE: "structured",
            OperatorType.GROUP_BY: "structured",
            OperatorType.COMPUTE_GRADIENT: "profile",
            OperatorType.COMPUTE_MLD: "profile",
            OperatorType.COMPUTE_ANOMALY: "profile",
            OperatorType.COMPUTE_STATS: "profile",
            OperatorType.SEMANTIC_SEARCH: "semantic",
            OperatorType.JOIN: "structured",
            OperatorType.VISUALIZE: "visualization"
        }
        
        self.memory = None  # Will be initialized with memory system
    
    async def plan(
        self,
        dag: SemanticOperatorDAG,
        deadline_ms: Optional[int] = None
    ) -> ExecutionPlan:
        """
        Generate an optimized execution plan from a semantic operator DAG.
        
        Args:
            dag: Semantic operator DAG
            deadline_ms: Optional deadline constraint in milliseconds
        
        Returns:
            Optimized ExecutionPlan
        """
        plan_id = str(uuid.uuid4())
        logger.info(f"Planning execution for {len(dag.operators)} operators")
        
        # Step 1: Estimate costs for all operators
        cost_estimates = await self._estimate_costs(dag)
        
        # Step 2: Build execution order (topological sort)
        execution_order = dag.topological_sort()
        
        # Step 3: Identify parallel execution groups
        parallel_groups = self._identify_parallel_groups(dag, execution_order)
        
        # Step 4: Generate execution steps
        steps = []
        for op_id in execution_order:
            op = dag.get_operator(op_id)
            if op:
                step = await self._create_step(op, cost_estimates.get(op_id), dag)
                steps.append(step)
        
        # Step 5: Calculate total estimated cost
        total_cost = sum(s.operator.estimated_cost for s in steps)
        
        # Step 6: Apply deadline-aware optimization if needed
        if deadline_ms and total_cost > deadline_ms:
            steps = await self._optimize_for_deadline(steps, deadline_ms)
            total_cost = sum(s.operator.estimated_cost for s in steps)
        
        # Step 7: Generate cache strategy
        cache_strategy = self._generate_cache_strategy(steps)
        
        plan = ExecutionPlan(
            steps=steps,
            estimated_cost=total_cost,
            cache_strategy=cache_strategy,
            parallel_groups=parallel_groups,
            deadline_ms=deadline_ms,
            plan_id=plan_id
        )
        
        logger.info(f"Generated plan {plan_id} with estimated cost {total_cost:.2f}ms")
        
        return plan
    
    async def _estimate_costs(
        self,
        dag: SemanticOperatorDAG
    ) -> Dict[str, CostEstimate]:
        """Estimate costs for all operators in the DAG."""
        estimates = {}
        
        for op in dag.operators:
            base = self.base_costs.get(op.type, 50)
            
            # Adjust based on parameters
            adjusted = base
            
            # Check for selectivity hints
            if op.type == OperatorType.SPATIAL_FILTER:
                bbox = op.params.get("bbox", [])
                if bbox:
                    # Larger areas = more data = higher cost
                    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    adjusted = base * (1 + area / 1000)
            
            elif op.type == OperatorType.TEMPORAL_FILTER:
                # Longer time ranges = higher cost
                # Assume params has 'start' and 'end'
                adjusted = base * 1.5  # Default adjustment
            
            # Check cache availability
            cache_key = self._generate_cache_key(op)
            cached_result = await cache_get(cache_key) if cache_key else None
            cache_available = cached_result is not None
            
            if cache_available:
                adjusted *= 0.05  # 95% reduction for cache hit
            
            # Check historical costs from memory
            historical = None
            if self.memory:
                historical = await self._get_historical_cost(op)
                if historical:
                    # Blend with historical data
                    adjusted = 0.7 * adjusted + 0.3 * historical
            
            estimates[op.id] = CostEstimate(
                base_cost=base,
                adjusted_cost=adjusted,
                cache_available=cache_available,
                historical_cost=historical
            )
            
            # Update operator's estimated cost
            op.estimated_cost = adjusted
        
        return estimates
    
    def _identify_parallel_groups(
        self,
        dag: SemanticOperatorDAG,
        execution_order: List[str]
    ) -> List[List[int]]:
        """
        Identify groups of operators that can run in parallel.
        Returns list of step index groups.
        """
        groups = []
        current_group = []
        completed = set()
        
        for i, op_id in enumerate(execution_order):
            # Check if all dependencies are completed
            deps = dag.get_dependencies(op_id)
            if all(d in completed for d in deps):
                if not current_group:
                    current_group.append(i)
                else:
                    # Check if this can run in parallel with current group
                    can_parallel = True
                    for group_idx in current_group:
                        group_op_id = execution_order[group_idx]
                        if group_op_id in deps or op_id in dag.get_dependencies(group_op_id):
                            can_parallel = False
                            break
                    
                    if can_parallel:
                        current_group.append(i)
                    else:
                        groups.append(current_group)
                        current_group = [i]
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [i]
            
            completed.add(op_id)
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    async def _create_step(
        self,
        op: Operator,
        estimate: Optional[CostEstimate],
        dag: SemanticOperatorDAG
    ) -> ExecutionStep:
        """Create an execution step from an operator."""
        server = self.server_assignments.get(op.type, "structured")
        
        # Generate cache key
        cache_key = self._generate_cache_key(op)
        
        # Determine timeout (3x estimated cost, minimum 1s)
        timeout = max(1000, int(op.estimated_cost * 3))
        
        # Get dependencies
        deps = dag.get_dependencies(op.id)
        
        return ExecutionStep(
            operator=op,
            mcp_server=server,
            cache_key=cache_key,
            timeout=timeout,
            depends_on=deps
        )
    
    async def _optimize_for_deadline(
        self,
        steps: List[ExecutionStep],
        deadline_ms: int
    ) -> List[ExecutionStep]:
        """
        Optimize execution plan to meet deadline constraint.
        May sacrifice accuracy for speed.
        """
        current_cost = sum(s.operator.estimated_cost for s in steps)
        
        if current_cost <= deadline_ms:
            return steps
        
        # Strategy 1: Skip visualization if under pressure
        if current_cost > deadline_ms * 1.5:
            steps = [s for s in steps if s.operator.type != OperatorType.VISUALIZE]
        
        # Strategy 2: Reduce computation precision
        for step in steps:
            if step.operator.type in [
                OperatorType.COMPUTE_GRADIENT,
                OperatorType.COMPUTE_MLD,
                OperatorType.COMPUTE_ANOMALY
            ]:
                step.operator.params["fast_mode"] = True
                step.operator.estimated_cost *= 0.5
        
        # Strategy 3: Add sampling if still over budget
        current_cost = sum(s.operator.estimated_cost for s in steps)
        if current_cost > deadline_ms:
            for step in steps:
                if step.operator.type in [
                    OperatorType.SPATIAL_FILTER,
                    OperatorType.TEMPORAL_FILTER
                ]:
                    step.operator.params["sample_rate"] = 0.5
                    step.operator.estimated_cost *= 0.6
        
        logger.warning(f"Applied deadline optimization: {current_cost:.0f}ms -> {sum(s.operator.estimated_cost for s in steps):.0f}ms")
        
        return steps
    
    def _generate_cache_key(self, op: Operator) -> Optional[str]:
        """Generate a normalized cache key for an operator."""
        import hashlib
        import json
        
        # Sort params for normalization
        sorted_params = json.dumps(op.params, sort_keys=True)
        op_type_str = op.type.value if hasattr(op.type, 'value') else str(op.type)
        key_content = f"{op_type_str}:{sorted_params}"
        
        return f"op:{hashlib.sha256(key_content.encode()).hexdigest()[:16]}"
    
    def _generate_cache_strategy(
        self,
        steps: List[ExecutionStep]
    ) -> Dict[str, Any]:
        """Generate caching strategy for the execution plan."""
        cacheable_steps = []
        ttl_policy = {}
        
        for i, step in enumerate(steps):
            if step.cache_key:
                cacheable_steps.append(i)
                
                # Determine TTL based on operator type
                if step.operator.type in [
                    OperatorType.SPATIAL_FILTER,
                    OperatorType.TEMPORAL_FILTER
                ]:
                    # Data queries - longer TTL for historical, shorter for recent
                    ttl_policy[step.cache_key] = 3600  # 1 hour default
                elif step.operator.type == OperatorType.VISUALIZE:
                    ttl_policy[step.cache_key] = 300  # 5 minutes
                else:
                    ttl_policy[step.cache_key] = 1800  # 30 minutes
        
        return {
            "cacheable_steps": cacheable_steps,
            "ttl_policy": ttl_policy,
            "enable_cache": True
        }
    
    async def _get_historical_cost(self, op: Operator) -> Optional[float]:
        """Get historical cost from memory system."""
        if not self.memory:
            return None
        
        # TODO: Implement when memory system is connected
        return None
