"""
Planner Memory - Learns from query planning patterns.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import hashlib

from core.logging import get_logger
from models.operators import ExecutionPlan, SemanticOperatorDAG
from .memory_store import MemoryStore, MemoryEntry

logger = get_logger(__name__)


@dataclass
class PlanPattern:
    """A learned planning pattern."""
    operator_sequence: List[str]
    estimated_cost: float
    actual_cost: float
    parallel_groups: List[List[int]]
    success_rate: float


class PlannerMemory:
    """
    Memory system for query planning.
    
    Learns:
    - Optimal execution plans for query patterns
    - Cost estimation improvements
    - Parallelization opportunities
    - Server routing decisions
    """
    
    def __init__(self):
        self.store = MemoryStore("planner")
        
        # Historical cost data for ML-based estimation
        self.operator_costs: Dict[str, List[float]] = {}
    
    async def record_plan(
        self,
        dag: SemanticOperatorDAG,
        plan: ExecutionPlan,
        actual_cost: float
    ):
        """Record an executed plan for learning."""
        # Generate pattern hash from operator sequence
        op_sequence = [(op.type.value if hasattr(op.type, 'value') else str(op.type)) for op in dag.operators]
        sequence_hash = hashlib.sha256(
            ",".join(op_sequence).encode()
        ).hexdigest()[:16]
        
        entry = MemoryEntry(
            id=f"plan_{sequence_hash}",
            type="plan_pattern",
            content={
                "operators": op_sequence,
                "estimated_cost": plan.estimated_cost,
                "actual_cost": actual_cost,
                "parallel_groups": plan.parallel_groups,
                "cache_strategy": plan.cache_strategy,
                "step_count": len(plan.steps)
            },
            success_rate=min(1.0, plan.estimated_cost / max(actual_cost, 1))
        )
        
        await self.store.store(entry, long_term=True)
        
        # Update operator cost history
        await self._update_operator_costs(plan, actual_cost)
        
        logger.debug(f"Recorded plan pattern: {sequence_hash}")
    
    async def get_historical_cost(
        self,
        operator_type: str,
        params: Dict[str, Any]
    ) -> Optional[float]:
        """Get historical cost for an operator type."""
        costs = self.operator_costs.get(operator_type, [])
        
        if not costs:
            return None
        
        # Return weighted average (more recent = higher weight)
        if len(costs) == 1:
            return costs[0]
        
        weights = [0.5 ** i for i in range(len(costs))]
        weighted_sum = sum(c * w for c, w in zip(costs, weights))
        weight_total = sum(weights)
        
        return weighted_sum / weight_total
    
    async def find_similar_plans(
        self,
        dag: SemanticOperatorDAG,
        query_embedding: List[float],
        n_results: int = 3
    ) -> List[PlanPattern]:
        """Find similar previous plans."""
        entries = await self.store.search(
            query_embedding,
            n_results,
            filter_type="plan_pattern"
        )
        
        patterns = []
        for entry in entries:
            patterns.append(PlanPattern(
                operator_sequence=entry.content.get("operators", []),
                estimated_cost=entry.content.get("estimated_cost", 0),
                actual_cost=entry.content.get("actual_cost", 0),
                parallel_groups=entry.content.get("parallel_groups", []),
                success_rate=entry.success_rate
            ))
        
        return patterns
    
    async def get_best_plan_for_pattern(
        self,
        op_sequence: List[str]
    ) -> Optional[PlanPattern]:
        """Get the best historical plan for an operator sequence."""
        sequence_hash = hashlib.sha256(
            ",".join(op_sequence).encode()
        ).hexdigest()[:16]
        
        entry = await self.store.retrieve(f"plan_{sequence_hash}")
        
        if entry and entry.success_rate >= 0.7:
            return PlanPattern(
                operator_sequence=entry.content.get("operators", []),
                estimated_cost=entry.content.get("estimated_cost", 0),
                actual_cost=entry.content.get("actual_cost", 0),
                parallel_groups=entry.content.get("parallel_groups", []),
                success_rate=entry.success_rate
            )
        
        return None
    
    async def update_plan_feedback(
        self,
        plan_id: str,
        success: bool,
        actual_cost: Optional[float] = None
    ):
        """Update plan pattern with execution feedback."""
        await self.store.update_success_rate(plan_id, success)
        
        if actual_cost is not None:
            entry = await self.store.retrieve(plan_id)
            if entry:
                entry.content["actual_cost"] = actual_cost
                await self.store.store(entry)
    
    async def _update_operator_costs(
        self,
        plan: ExecutionPlan,
        total_actual_cost: float
    ):
        """Update operator cost history based on execution."""
        if not plan.steps:
            return
        
        # Distribute actual cost proportionally based on estimated costs
        estimated_total = sum(s.operator.estimated_cost for s in plan.steps)
        if estimated_total == 0:
            return
        
        for step in plan.steps:
            op_type = step.operator.type.value if hasattr(step.operator.type, 'value') else str(step.operator.type)
            proportion = step.operator.estimated_cost / estimated_total
            actual_op_cost = total_actual_cost * proportion
            
            if op_type not in self.operator_costs:
                self.operator_costs[op_type] = []
            
            # Keep last 100 measurements
            self.operator_costs[op_type].insert(0, actual_op_cost)
            self.operator_costs[op_type] = self.operator_costs[op_type][:100]
