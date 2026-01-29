"""
Iterative Refiner - Handles query and result refinement.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from core.logging import get_logger
from models.responses import QueryResult, VisualizationSpec

logger = get_logger(__name__)


@dataclass
class RefinementSuggestion:
    """A suggestion for refining the query or results."""
    type: str  # clarification, filter, visualization, expansion
    message: str
    options: Optional[List[str]] = None
    confidence: float = 0.8


class IterativeRefiner:
    """
    Handles iterative refinement of queries and results.
    
    Capabilities:
    - Detect when clarification is needed
    - Suggest query refinements
    - Improve results based on feedback
    - Learn from user interactions
    """
    
    def __init__(self, memory=None):
        self.memory = memory
        self.min_confidence_threshold = 0.7
    
    async def should_refine(
        self,
        result: QueryResult,
        user_feedback: Optional[str] = None
    ) -> bool:
        """Determine if refinement is needed."""
        # Low confidence
        if result.confidence < self.min_confidence_threshold:
            return True
        
        # Empty or minimal results
        if not result.data or (isinstance(result.data, list) and len(result.data) < 3):
            return True
        
        # User indicated dissatisfaction
        if user_feedback and any(
            word in user_feedback.lower()
            for word in ["not what", "wrong", "different", "more", "less", "other"]
        ):
            return True
        
        return False
    
    async def refine(
        self,
        original_query: str,
        dag: Any,
        initial_result: Any,
        max_iterations: int = 3
    ) -> tuple:
        """
        Iteratively refine the query and results until confidence is acceptable.
        
        Args:
            original_query: The original natural language query
            dag: The semantic operator DAG
            initial_result: Initial execution result
            max_iterations: Maximum refinement iterations
        
        Returns:
            tuple: (refined_result, iteration_count)
        """
        result = initial_result
        iterations = 0
        
        for i in range(max_iterations):
            if result.confidence >= self.min_confidence_threshold:
                break
            
            iterations += 1
            logger.info(f"Refinement iteration {i+1}: confidence={result.confidence:.2f}")
            
            # For now, just return as-is since full refinement needs MCP re-execution
            # In a full implementation, we would:
            # 1. Analyze why confidence is low
            # 2. Modify the DAG or parameters
            # 3. Re-execute through MCP
            break
        
        return result, iterations
    
    async def get_suggestions(
        self,
        query: str,
        result: QueryResult,
        context: Dict[str, Any]
    ) -> List[RefinementSuggestion]:
        """Get refinement suggestions based on query and result."""
        suggestions = []
        
        # Check for ambiguity
        if result.confidence < 0.8:
            suggestions.extend(await self._get_clarification_suggestions(query, context))
        
        # Check for too many/few results
        if isinstance(result.data, list):
            if len(result.data) > 1000:
                suggestions.append(RefinementSuggestion(
                    type="filter",
                    message="Your query returned many results. Would you like to narrow down?",
                    options=[
                        "Focus on recent data only",
                        "Limit to specific region",
                        "Filter by quality flags"
                    ]
                ))
            elif len(result.data) < 10:
                suggestions.append(RefinementSuggestion(
                    type="expansion",
                    message="Your query returned few results. Would you like to expand the search?",
                    options=[
                        "Extend time range",
                        "Expand geographic area",
                        "Include lower quality data"
                    ]
                ))
        
        # Suggest additional visualizations
        if result.visualizations and len(result.visualizations) < 2:
            suggestions.append(RefinementSuggestion(
                type="visualization",
                message="Would you like additional visualizations?",
                options=[
                    "Add trajectory map",
                    "Add time series chart",
                    "Add vertical profile comparison"
                ]
            ))
        
        return suggestions
    
    async def apply_refinement(
        self,
        original_query: str,
        refinement: str,
        context: Dict[str, Any]
    ) -> str:
        """Apply a refinement to the query."""
        refinement_lower = refinement.lower()
        
        # Time-based refinements
        if "recent" in refinement_lower or "last" in refinement_lower:
            if "30 days" not in original_query and "month" not in original_query:
                return f"{original_query} from the last 30 days"
        
        if "year" in refinement_lower:
            return f"{original_query} for 2024"
        
        # Quality refinements
        if "quality" in refinement_lower or "good" in refinement_lower:
            return f"{original_query} with good quality data only"
        
        # Spatial refinements
        if "coastal" in refinement_lower:
            return f"{original_query} in coastal regions"
        
        if "deep" in refinement_lower:
            return f"{original_query} for depths below 500m"
        
        # If no specific pattern matched, append the refinement
        return f"{original_query} {refinement}"
    
    async def generate_clarification(
        self,
        query: str,
        ambiguity_type: str,
        context: Dict[str, Any]
    ) -> RefinementSuggestion:
        """Generate a clarification question."""
        clarifications = {
            "temporal": RefinementSuggestion(
                type="clarification",
                message="Which time period are you interested in?",
                options=[
                    "Last 7 days",
                    "Last 30 days",
                    "Last year",
                    "All available data"
                ]
            ),
            "spatial": RefinementSuggestion(
                type="clarification",
                message="Which region would you like to focus on?",
                options=[
                    "Arabian Sea",
                    "Bay of Bengal",
                    "Indian Ocean",
                    "Global"
                ]
            ),
            "parameter": RefinementSuggestion(
                type="clarification",
                message="Which oceanographic parameter are you interested in?",
                options=[
                    "Temperature",
                    "Salinity",
                    "Both temperature and salinity",
                    "All available parameters"
                ]
            ),
            "depth": RefinementSuggestion(
                type="clarification",
                message="What depth range are you interested in?",
                options=[
                    "Surface (0-100m)",
                    "Mixed layer",
                    "Deep ocean (>1000m)",
                    "Full profile"
                ]
            )
        }
        
        return clarifications.get(ambiguity_type, RefinementSuggestion(
            type="clarification",
            message="Could you please provide more details about your query?",
            options=None
        ))
    
    async def refine_visualization(
        self,
        viz: VisualizationSpec,
        feedback: str
    ) -> VisualizationSpec:
        """Refine a visualization based on feedback."""
        feedback_lower = feedback.lower()
        
        # Color scheme changes
        if "color" in feedback_lower:
            if "blue" in feedback_lower or "cool" in feedback_lower:
                viz.spec.get("layout", {})["colorscale"] = "Blues"
            elif "red" in feedback_lower or "warm" in feedback_lower:
                viz.spec.get("layout", {})["colorscale"] = "Reds"
        
        # Size changes
        if "bigger" in feedback_lower or "larger" in feedback_lower:
            if "layout" in viz.spec:
                viz.spec["layout"]["height"] = viz.spec["layout"].get("height", 500) * 1.5
                viz.spec["layout"]["width"] = viz.spec["layout"].get("width", 800) * 1.5
        
        if "smaller" in feedback_lower:
            if "layout" in viz.spec:
                viz.spec["layout"]["height"] = viz.spec["layout"].get("height", 500) * 0.7
                viz.spec["layout"]["width"] = viz.spec["layout"].get("width", 800) * 0.7
        
        return viz
    
    async def _get_clarification_suggestions(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> List[RefinementSuggestion]:
        """Get clarification suggestions for an ambiguous query."""
        suggestions = []
        query_lower = query.lower()
        
        # Check for missing temporal context
        temporal_words = ["when", "today", "yesterday", "week", "month", "year", "2024", "2023"]
        if not any(word in query_lower for word in temporal_words):
            suggestions.append(RefinementSuggestion(
                type="clarification",
                message="What time period should I analyze?",
                options=["Recent (last 30 days)", "Last year", "All available"],
                confidence=0.7
            ))
        
        # Check for vague spatial context
        if "ocean" in query_lower and not any(
            word in query_lower
            for word in ["arabian", "bengal", "atlantic", "pacific", "indian"]
        ):
            suggestions.append(RefinementSuggestion(
                type="clarification",
                message="Which ocean region specifically?",
                options=["Arabian Sea", "Bay of Bengal", "North Indian Ocean", "Global"],
                confidence=0.7
            ))
        
        return suggestions
