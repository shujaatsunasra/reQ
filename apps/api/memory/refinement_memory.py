"""
Refinement Memory - Learns from iterative refinement patterns.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import hashlib
import uuid

from core.logging import get_logger
from .memory_store import MemoryStore, MemoryEntry

logger = get_logger(__name__)


@dataclass
class RefinementPattern:
    """A learned refinement pattern."""
    initial_query: str
    refined_query: str
    refinement_type: str
    success_delta: float
    user_feedback: Optional[str] = None


class RefinementMemory:
    """
    Memory system for iterative refinement.
    
    Learns:
    - Query refinement strategies
    - User feedback patterns
    - Clarification dialogues
    - Result improvement techniques
    """
    
    def __init__(self):
        self.store = MemoryStore("refinement")
    
    async def record_refinement(
        self,
        session_id: str,
        initial_query: str,
        refined_query: str,
        refinement_type: str,
        initial_confidence: float,
        refined_confidence: float,
        user_feedback: Optional[str] = None
    ):
        """Record a refinement action."""
        refinement_id = f"ref_{uuid.uuid4().hex[:12]}"
        
        success_delta = refined_confidence - initial_confidence
        
        entry = MemoryEntry(
            id=refinement_id,
            type="refinement",
            content={
                "session_id": session_id,
                "initial_query": initial_query,
                "refined_query": refined_query,
                "refinement_type": refinement_type,
                "initial_confidence": initial_confidence,
                "refined_confidence": refined_confidence,
                "success_delta": success_delta,
                "user_feedback": user_feedback
            },
            success_rate=max(0, min(1, 0.5 + success_delta)),
            metadata={
                "refinement_type": refinement_type
            }
        )
        
        # Store long-term if refinement improved results
        await self.store.store(entry, long_term=success_delta > 0)
        
        logger.debug(f"Recorded refinement: {refinement_type}, delta={success_delta:.2f}")
    
    async def record_clarification(
        self,
        session_id: str,
        original_query: str,
        clarification_question: str,
        user_response: str,
        resolved_query: str
    ):
        """Record a clarification dialogue."""
        clarification_id = f"clar_{uuid.uuid4().hex[:12]}"
        
        entry = MemoryEntry(
            id=clarification_id,
            type="clarification",
            content={
                "session_id": session_id,
                "original_query": original_query,
                "question": clarification_question,
                "response": user_response,
                "resolved_query": resolved_query
            },
            metadata={
                "clarification_type": self._classify_clarification(clarification_question)
            }
        )
        
        await self.store.store(entry, long_term=True)
    
    async def record_user_feedback(
        self,
        session_id: str,
        query: str,
        result_quality: float,  # 0-1 scale
        feedback_text: Optional[str] = None,
        feedback_type: str = "explicit"  # explicit, implicit
    ):
        """Record user feedback on query results."""
        feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
        
        entry = MemoryEntry(
            id=feedback_id,
            type="feedback",
            content={
                "session_id": session_id,
                "query": query,
                "quality": result_quality,
                "text": feedback_text,
                "feedback_type": feedback_type
            },
            success_rate=result_quality
        )
        
        await self.store.store(entry)
    
    async def get_refinement_suggestions(
        self,
        query: str,
        query_embedding: List[float],
        current_confidence: float
    ) -> List[Dict[str, Any]]:
        """Get refinement suggestions based on similar past queries."""
        entries = await self.store.search(
            query_embedding,
            n_results=5,
            filter_type="refinement"
        )
        
        suggestions = []
        for entry in entries:
            if entry.success_rate > 0.6:
                suggestions.append({
                    "type": entry.content.get("refinement_type"),
                    "strategy": entry.content.get("refined_query"),
                    "expected_improvement": entry.content.get("success_delta"),
                    "confidence": entry.success_rate
                })
        
        return sorted(suggestions, key=lambda x: x["expected_improvement"], reverse=True)
    
    async def get_clarification_patterns(
        self,
        query: str,
        ambiguity_type: str
    ) -> List[str]:
        """Get clarification question patterns for ambiguous queries."""
        # Would search for similar ambiguity patterns
        patterns = {
            "temporal": [
                "Which time period are you interested in?",
                "Do you want recent data or historical data?",
                "Should I show the last month, year, or all available data?"
            ],
            "spatial": [
                "Which region specifically?",
                "Do you want the entire ocean or a specific area?",
                "Should I focus on coastal or open ocean areas?"
            ],
            "parameter": [
                "Which parameter would you like to analyze?",
                "Are you interested in temperature, salinity, or both?",
                "Should I include derived parameters like MLD?"
            ],
            "visualization": [
                "How would you like to see the results?",
                "Would you prefer a map, chart, or table?",
                "Should I generate multiple visualization types?"
            ]
        }
        
        return patterns.get(ambiguity_type, [
            "Could you please clarify your request?",
            "What specific aspect are you interested in?"
        ])
    
    async def learn_from_session(
        self,
        session_id: str,
        queries: List[Dict[str, Any]],
        final_satisfaction: float
    ):
        """Learn from a complete session's refinement journey."""
        if len(queries) < 2:
            return
        
        # Analyze the refinement journey
        journey = []
        for i in range(1, len(queries)):
            prev = queries[i - 1]
            curr = queries[i]
            
            journey.append({
                "from": prev.get("query"),
                "to": curr.get("query"),
                "confidence_change": curr.get("confidence", 0) - prev.get("confidence", 0)
            })
        
        # Store the journey pattern
        entry = MemoryEntry(
            id=f"session_{session_id}",
            type="session_journey",
            content={
                "session_id": session_id,
                "query_count": len(queries),
                "journey": journey,
                "final_satisfaction": final_satisfaction
            },
            success_rate=final_satisfaction
        )
        
        await self.store.store(entry, long_term=final_satisfaction > 0.7)
    
    def _classify_clarification(self, question: str) -> str:
        """Classify the type of clarification question."""
        question_lower = question.lower()
        
        if any(w in question_lower for w in ["when", "time", "date", "period"]):
            return "temporal"
        if any(w in question_lower for w in ["where", "region", "area", "location"]):
            return "spatial"
        if any(w in question_lower for w in ["what", "which", "parameter", "variable"]):
            return "parameter"
        if any(w in question_lower for w in ["how", "show", "display", "visualize"]):
            return "visualization"
        
        return "general"
