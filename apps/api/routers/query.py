"""
Query processing endpoints.
Main entry point for natural language queries.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time
import uuid

from core.logging import get_logger
from core.llm_service import get_llm_service
from nl2op import NL2Operator
from planner import QueryPlanner
from security import MCPBridge
from mcp import MCPOrchestrator
from refiner import IterativeRefiner
from models.operators import SemanticOperatorDAG, ExecutionPlan
from models.responses import QueryResponse, VisualizationSpec
from core.visualization_suggestions import suggest_visualizations

logger = get_logger(__name__)
router = APIRouter()

# Initialize components
nl2op = NL2Operator()
planner = QueryPlanner()
bridge = MCPBridge()
orchestrator = MCPOrchestrator()
refiner = IterativeRefiner()


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str = Field(..., description="Natural language query", min_length=1, max_length=2000)
    mode: str = Field(default="explorer", description="UI mode: explorer or power")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Conversation context")
    deadline_ms: Optional[int] = Field(default=None, description="Maximum execution time in milliseconds")
    user_id: Optional[str] = Field(default=None, description="User identifier for rate limiting")
    groq_api_key: Optional[str] = Field(default=None, description="Groq API key (primary provider)")
    huggingface_api_key: Optional[str] = Field(default=None, description="HuggingFace API key (fallback provider)")


class QueryResult(BaseModel):
    """Response model for query endpoint."""
    success: bool
    request_id: str
    query: str
    response: Optional[str] = None  # Natural language response from LLM
    interpretation: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    visualizations: Optional[List[Dict[str, Any]]] = None
    confidence: float
    execution_time_ms: float
    refinement_iterations: int = 0
    alternatives: Optional[List[Dict[str, Any]]] = None
    error: Optional[Dict[str, str]] = None
    suggested_visualizations: Optional[List[Dict[str, Any]]] = None  # AI-recommended viz types
    
    # Power mode extras
    operator_dag: Optional[Dict[str, Any]] = None
    execution_plan: Optional[Dict[str, Any]] = None
    cost_metrics: Optional[Dict[str, Any]] = None


@router.post("/query", response_model=QueryResult)
async def process_query(request: QueryRequest) -> QueryResult:
    """
    Process a natural language query about oceanographic data.
    
    This endpoint orchestrates the full query processing pipeline:
    1. NL2Operator: Parse natural language into semantic operators
    2. Query Planner: Generate optimized execution plan
    3. MCP Bridge: Validate and secure the request
    4. MCP Servers: Execute the query across specialized servers
    5. Iterative Refinement: Improve results if confidence is low
    6. Visualization: Generate appropriate visualizations
    
    Args:
        request: Query request with natural language query and options
    
    Returns:
        QueryResult with data, visualizations, and metadata
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"Processing query [{request_id}]: {request.query[:100]}...")
    
    try:
        # Step 1: Parse natural language into semantic operators
        dag = await nl2op.parse(
            query=request.query,
            context=request.context,
            mode=request.mode
        )
        
        if dag.confidence < 0.7 and dag.alternatives:
            # Return alternatives for clarification
            return QueryResult(
                success=True,
                request_id=request_id,
                query=request.query,
                confidence=dag.confidence,
                execution_time_ms=(time.time() - start_time) * 1000,
                alternatives=[alt.model_dump() for alt in dag.alternatives],
                error={
                    "code": "CLARIFICATION_NEEDED",
                    "message": "Query is ambiguous. Please select an interpretation."
                }
            )
        
        # Step 2: Generate execution plan
        plan = await planner.plan(
            dag=dag,
            deadline_ms=request.deadline_ms
        )
        
        # Step 3: Validate through MCP Bridge security
        validation = await bridge.validate(query=request.query, dag=dag, user_id=request.user_id)
        if not validation.passed:
            return QueryResult(
                success=False,
                request_id=request_id,
                query=request.query,
                confidence=0.0,
                execution_time_ms=(time.time() - start_time) * 1000,
                error={
                    "code": "SECURITY_VIOLATION",
                    "message": "; ".join(validation.issues) if validation.issues else "Security check failed"
                }
            )
        
        # Step 4: Execute through MCP Orchestrator
        result = await orchestrator.execute(plan)
        
        # Step 5: Iterative refinement if confidence is low
        refinement_iterations = 0
        if result.confidence < 0.8:
            result, refinement_iterations = await refiner.refine(
                original_query=request.query,
                dag=dag,
                initial_result=result,
                max_iterations=3
            )
        
        # Step 6: Generate visualizations
        visualizations = await orchestrator.generate_visualizations(
            data=result.data,
            query_intent=dag.intent
        )
        
        # Step 7: Generate natural language response using LLM
        # Use frontend-provided keys if available, otherwise fall back to server config
        from core.llm_service import LLMService
        llm = LLMService(
            groq_api_key=request.groq_api_key,
            huggingface_api_key=request.huggingface_api_key
        )
        llm_response = await llm.generate_response(
            query=request.query,
            data=result.data,
            context=f"Intent: {dag.intent}"
        )
        
        execution_time = (time.time() - start_time) * 1000
        logger.info(f"Query [{request_id}] completed in {execution_time:.2f}ms")
        
        # Combine LLM confidence with execution confidence
        final_confidence = (result.confidence + llm_response.get("confidence", 0.5)) / 2
        
        # Build response
        response = QueryResult(
            success=True,
            request_id=request_id,
            query=request.query,
            response=llm_response.get("response", "Query processed successfully."),
            interpretation={
                "intent": dag.intent,
                "entities": dag.entities,
                "operators_count": len(dag.operators)
            },
            data=result.data,
            visualizations=[v.model_dump() for v in visualizations],
            confidence=final_confidence,
            execution_time_ms=execution_time,
            refinement_iterations=refinement_iterations,
            suggested_visualizations=suggest_visualizations(request.query, result.data)
        )
        
        # Add power mode extras
        if request.mode == "power":
            response.operator_dag = dag.model_dump()
            response.execution_plan = plan.model_dump()
            response.cost_metrics = {
                "predicted_cost_ms": plan.estimated_cost,
                "actual_cost_ms": execution_time,
                "cache_hits": result.cache_hits,
                "rows_processed": result.rows_processed
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Query [{request_id}] failed: {str(e)}")
        return QueryResult(
            success=False,
            request_id=request_id,
            query=request.query,
            confidence=0.0,
            execution_time_ms=(time.time() - start_time) * 1000,
            error={
                "code": "PROCESSING_ERROR",
                "message": str(e)
            }
        )


@router.post("/query/explain")
async def explain_query(request: QueryRequest) -> Dict[str, Any]:
    """
    Explain how a query would be processed without executing it.
    Useful for understanding query interpretation in Power mode.
    """
    try:
        # Parse but don't execute
        dag = await nl2op.parse(
            query=request.query,
            context=request.context,
            mode=request.mode
        )
        
        plan = await planner.plan(dag=dag)
        
        return {
            "success": True,
            "query": request.query,
            "interpretation": {
                "intent": dag.intent,
                "entities": dag.entities,
                "confidence": dag.confidence
            },
            "operators": [op.model_dump() for op in dag.operators],
            "execution_plan": {
                "steps": [step.model_dump() for step in plan.steps],
                "estimated_cost_ms": plan.estimated_cost,
                "parallel_groups": plan.parallel_groups
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
