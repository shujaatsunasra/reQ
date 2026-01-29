"""
Operator generation from extracted entities.
Converts entities into semantic operators for execution.
"""

import uuid
from typing import List, Tuple, Optional, Dict, Any

from core.logging import get_logger
from models.operators import Operator, Edge, OperatorType
from models.entities import ExtractedEntities
from .domain_knowledge import INTENT_VISUALIZATIONS

logger = get_logger(__name__)


class OperatorGenerator:
    """
    Generates semantic operators from extracted entities.
    
    Creates a DAG of operators that can be executed by MCP servers.
    """
    
    def __init__(self):
        # Mapping of operator types to MCP servers
        self.server_mapping = {
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
        
        # Base costs for operators (in ms)
        self.base_costs = {
            OperatorType.SPATIAL_FILTER: 50,
            OperatorType.TEMPORAL_FILTER: 30,
            OperatorType.PARAMETER_FILTER: 20,
            OperatorType.QC_FILTER: 20,
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
    
    async def generate(
        self,
        entities: ExtractedEntities,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Operator], List[Edge]]:
        """
        Generate semantic operators from extracted entities.
        
        Args:
            entities: Extracted entities from the query
            intent: Detected query intent
            context: Conversation context
        
        Returns:
            Tuple of (operators, edges)
        """
        operators = []
        edges = []
        
        # Track the current "tip" of the DAG for chaining
        last_op_id = None
        
        # Step 1: Generate filter operators
        
        # Spatial filter
        if entities.spatial:
            for spatial in entities.spatial:
                if spatial.bbox:
                    op = self._create_operator(
                        OperatorType.SPATIAL_FILTER,
                        {
                            "bbox": list(spatial.bbox),
                            "region_name": spatial.name
                        }
                    )
                    operators.append(op)
                    if last_op_id:
                        edges.append(Edge(from_id=last_op_id, to_id=op.id))
                    last_op_id = op.id
        
        # Temporal filter
        if entities.temporal:
            for temporal in entities.temporal:
                if temporal.start and temporal.end:
                    op = self._create_operator(
                        OperatorType.TEMPORAL_FILTER,
                        {
                            "start": temporal.start.isoformat(),
                            "end": temporal.end.isoformat(),
                            "type": temporal.type
                        }
                    )
                    operators.append(op)
                    if last_op_id:
                        edges.append(Edge(from_id=last_op_id, to_id=op.id))
                    last_op_id = op.id
        
        # Parameter filter
        if entities.parameters:
            params = [p.column for p in entities.parameters]
            op = self._create_operator(
                OperatorType.PARAMETER_FILTER,
                {
                    "parameters": params,
                    "include_qc": True
                }
            )
            operators.append(op)
            if last_op_id:
                edges.append(Edge(from_id=last_op_id, to_id=op.id))
            last_op_id = op.id
        
        # Float filter
        if entities.floats:
            float_ids = [f.float_id for f in entities.floats if f.float_id]
            if float_ids:
                op = self._create_operator(
                    OperatorType.FLOAT_FILTER,
                    {"float_ids": float_ids}
                )
                operators.append(op)
                if last_op_id:
                    edges.append(Edge(from_id=last_op_id, to_id=op.id))
                last_op_id = op.id
        
        # QC filter
        if entities.quality:
            qc_flags = []
            data_mode = None
            for qc in entities.quality:
                qc_flags.extend(qc.qc_flags)
                if qc.data_mode:
                    data_mode = qc.data_mode
            
            if qc_flags or data_mode:
                op = self._create_operator(
                    OperatorType.QC_FILTER,
                    {
                        "qc_flags": list(set(qc_flags)) if qc_flags else None,
                        "data_mode": data_mode
                    }
                )
                operators.append(op)
                if last_op_id:
                    edges.append(Edge(from_id=last_op_id, to_id=op.id))
                last_op_id = op.id
        
        # Step 2: Generate computation operators based on intent
        
        if intent == "gradient_analysis":
            param = entities.parameters[0].column if entities.parameters else "temperature"
            op = self._create_operator(
                OperatorType.COMPUTE_GRADIENT,
                {"parameter": param, "method": "finite_difference"}
            )
            operators.append(op)
            if last_op_id:
                edges.append(Edge(from_id=last_op_id, to_id=op.id))
            last_op_id = op.id
        
        elif intent == "mixed_layer_analysis":
            op = self._create_operator(
                OperatorType.COMPUTE_MLD,
                {"method": "temperature_threshold", "threshold": 0.5}
            )
            operators.append(op)
            if last_op_id:
                edges.append(Edge(from_id=last_op_id, to_id=op.id))
            last_op_id = op.id
        
        elif intent == "anomaly_detection":
            param = entities.parameters[0].column if entities.parameters else "temperature"
            op = self._create_operator(
                OperatorType.COMPUTE_ANOMALY,
                {"parameter": param, "baseline": "climatology"}
            )
            operators.append(op)
            if last_op_id:
                edges.append(Edge(from_id=last_op_id, to_id=op.id))
            last_op_id = op.id
        
        elif intent == "comparison":
            op = self._create_operator(
                OperatorType.COMPUTE_STATS,
                {"metrics": ["mean", "std", "min", "max"]}
            )
            operators.append(op)
            if last_op_id:
                edges.append(Edge(from_id=last_op_id, to_id=op.id))
            last_op_id = op.id
        
        # Step 3: Generate visualization operator
        viz_types = INTENT_VISUALIZATIONS.get(intent, ["time_series"])
        viz_op = self._create_operator(
            OperatorType.VISUALIZE,
            {
                "type": viz_types[0],
                "alternatives": viz_types[1:] if len(viz_types) > 1 else [],
                "parameters": [p.column for p in entities.parameters] if entities.parameters else ["temperature"]
            }
        )
        operators.append(viz_op)
        if last_op_id:
            edges.append(Edge(from_id=last_op_id, to_id=viz_op.id))
        
        return operators, edges
    
    def _create_operator(
        self,
        op_type: OperatorType,
        params: Dict[str, Any]
    ) -> Operator:
        """Create an operator with estimated cost."""
        op_id = f"{op_type.value}_{uuid.uuid4().hex[:8]}"
        
        return Operator(
            id=op_id,
            type=op_type,
            params=params,
            estimated_cost=self.base_costs.get(op_type, 50),
            target_server=self.server_mapping.get(op_type, "structured")
        )
