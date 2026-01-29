"""
Parsing Memory - Learns from query parsing patterns.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import hashlib
import uuid

from core.logging import get_logger
from models.entities import ExtractedEntities
from models.operators import SemanticOperatorDAG
from .memory_store import MemoryStore, MemoryEntry

logger = get_logger(__name__)


@dataclass
class ParsePattern:
    """A learned parsing pattern."""
    query_template: str
    entities: Dict[str, Any]
    operators: List[str]
    intent: str
    confidence: float


class ParsingMemory:
    """
    Memory system for query parsing.
    
    Learns:
    - Query patterns and their semantic interpretations
    - Entity extraction patterns
    - Intent classification improvements
    - Disambiguation resolutions
    """
    
    def __init__(self):
        self.store = MemoryStore("parsing")
    
    async def record_parse(
        self,
        query: str,
        entities: ExtractedEntities,
        dag: SemanticOperatorDAG,
        intent: str,
        confidence: float
    ):
        """Record a successful parse for learning."""
        # Generate query template by replacing specific values with placeholders
        template = self._extract_template(query, entities)
        template_hash = hashlib.sha256(template.encode()).hexdigest()[:16]
        
        entry = MemoryEntry(
            id=f"parse_{template_hash}",
            type="parse_pattern",
            content={
                "query": query,
                "template": template,
                "entities": entities.model_dump() if hasattr(entities, 'model_dump') else {},
                "operators": [(op.type.value if hasattr(op.type, 'value') else str(op.type)) for op in dag.operators],
                "intent": intent,
                "confidence": confidence
            },
            success_rate=confidence
        )
        
        await self.store.store(entry, long_term=confidence > 0.8)
        logger.debug(f"Recorded parse pattern: {template_hash}")
    
    async def find_similar_parses(
        self,
        query: str,
        query_embedding: List[float],
        n_results: int = 3
    ) -> List[ParsePattern]:
        """Find similar previous parses."""
        entries = await self.store.search(
            query_embedding,
            n_results,
            filter_type="parse_pattern"
        )
        
        patterns = []
        for entry in entries:
            if entry.success_rate >= 0.6:
                patterns.append(ParsePattern(
                    query_template=entry.content.get("template", ""),
                    entities=entry.content.get("entities", {}),
                    operators=entry.content.get("operators", []),
                    intent=entry.content.get("intent", ""),
                    confidence=entry.success_rate
                ))
        
        return patterns
    
    async def get_entity_patterns(
        self,
        entity_type: str
    ) -> List[Dict[str, Any]]:
        """Get learned patterns for a specific entity type."""
        # Search for entries with this entity type
        # In production, would use ChromaDB metadata filtering
        return []
    
    async def record_disambiguation(
        self,
        query: str,
        ambiguous_term: str,
        resolved_value: str,
        context: Dict[str, Any]
    ):
        """Record a disambiguation decision for learning."""
        entry = MemoryEntry(
            id=f"disamb_{uuid.uuid4().hex[:12]}",
            type="disambiguation",
            content={
                "query": query,
                "term": ambiguous_term,
                "resolved": resolved_value,
                "context": context
            }
        )
        
        await self.store.store(entry)
    
    async def update_parse_feedback(
        self,
        template_hash: str,
        success: bool
    ):
        """Update success rate based on feedback."""
        entry_id = f"parse_{template_hash}"
        await self.store.update_success_rate(entry_id, success)
    
    def _extract_template(
        self,
        query: str,
        entities: ExtractedEntities
    ) -> str:
        """
        Extract a query template by replacing specific values.
        
        Example:
        "Show temperature in Arabian Sea for 2024" ->
        "Show {PARAMETER} in {REGION} for {TIME}"
        """
        template = query
        
        if hasattr(entities, 'spatial') and entities.spatial:
            for region in entities.spatial:
                if hasattr(region, 'name'):
                    template = template.replace(region.name, "{REGION}")
        
        if hasattr(entities, 'temporal') and entities.temporal:
            if hasattr(entities.temporal, 'text'):
                template = template.replace(entities.temporal.text, "{TIME}")
        
        if hasattr(entities, 'parameters') and entities.parameters:
            for param in entities.parameters:
                template = template.replace(param, "{PARAMETER}")
        
        if hasattr(entities, 'float_ids') and entities.float_ids:
            for fid in entities.float_ids:
                template = template.replace(fid, "{FLOAT_ID}")
        
        return template
