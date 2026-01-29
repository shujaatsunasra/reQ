"""
NL2Operator - Natural Language to Semantic Operator Parser.
Transforms natural language queries into semantic operator DAGs.
"""

import uuid
from typing import Optional, Dict, Any, List
import spacy
from spacy.language import Language

from core.logging import get_logger
from models.operators import SemanticOperatorDAG, Operator, Edge, OperatorType
from models.entities import ExtractedEntities
from .entity_extractor import EntityExtractor
from .operator_generator import OperatorGenerator
from .domain_knowledge import OCEANOGRAPHIC_INTENTS

logger = get_logger(__name__)

# Global spaCy model instance
_nlp: Optional[Language] = None


def get_nlp() -> Language:
    """Get or load spaCy model."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_lg")
            logger.info("Loaded spaCy en_core_web_lg model")
        except OSError:
            # Fallback to smaller model
            _nlp = spacy.load("en_core_web_sm")
            logger.warning("Loaded spaCy en_core_web_sm model (fallback)")
    return _nlp


class NL2Operator:
    """
    Natural Language to Semantic Operator translator.
    
    Parses natural language queries into semantic operator DAGs that can be
    executed by the Query Planner and MCP servers.
    
    Processing steps:
    1. Tokenization with spaCy
    2. Named Entity Recognition (locations, dates, parameters)
    3. Dependency parsing for relationship extraction
    4. Domain mapping (e.g., "Arabian Sea" → bounding box)
    5. Operator generation from parsed structure
    6. Confidence scoring
    7. Alternative generation for ambiguous queries
    """
    
    def __init__(self):
        self.nlp = get_nlp()
        self.entity_extractor = EntityExtractor(self.nlp)
        self.operator_generator = OperatorGenerator()
        self.memory = None  # Will be initialized if memory systems are enabled
    
    async def parse(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        mode: str = "explorer"
    ) -> SemanticOperatorDAG:
        """
        Parse a natural language query into a semantic operator DAG.
        
        Args:
            query: Natural language query string
            context: Previous conversation context
            mode: UI mode (explorer/power) for complexity hints
        
        Returns:
            SemanticOperatorDAG with operators and confidence score
        """
        logger.info(f"Parsing query: {query[:100]}...")
        
        # Step 1: Process with spaCy
        doc = self.nlp(query)
        
        # Step 2: Extract entities
        entities = await self.entity_extractor.extract(doc, query)
        
        # Step 3: Detect intent
        intent = self._detect_intent(doc, entities)
        
        # Step 4: Generate operators from entities
        operators, edges = await self.operator_generator.generate(
            entities=entities,
            intent=intent,
            context=context
        )
        
        # Step 5: Calculate confidence
        confidence = self._calculate_confidence(entities, operators, intent)
        
        # Step 6: Generate alternatives if confidence is low
        alternatives = None
        if confidence < 0.7:
            alternatives = await self._generate_alternatives(
                query=query,
                doc=doc,
                entities=entities
            )
        
        # Step 7: Check memory for similar past queries
        if self.memory:
            memory_hints = await self._query_memory(query, entities)
            if memory_hints:
                confidence = min(1.0, confidence + 0.1)
        
        dag = SemanticOperatorDAG(
            operators=operators,
            edges=edges,
            confidence=confidence,
            intent=intent,
            entities=entities.to_dict(),
            alternatives=alternatives
        )
        
        logger.info(f"Parsed query with {len(operators)} operators, confidence: {confidence:.2f}")
        
        return dag
    
    def _detect_intent(
        self,
        doc: spacy.tokens.Doc,
        entities: ExtractedEntities
    ) -> str:
        """Detect the query intent from parsed document and entities."""
        text = doc.text.lower()
        
        # Check for specific intent patterns
        for intent, patterns in OCEANOGRAPHIC_INTENTS.items():
            for pattern in patterns:
                if pattern in text:
                    return intent
        
        # Default intent based on entities
        if entities.temporal and not entities.spatial:
            return "time_series_analysis"
        elif entities.spatial and not entities.temporal:
            return "spatial_analysis"
        elif entities.parameters and len(entities.parameters) > 1:
            return "comparison"
        elif entities.floats:
            return "float_tracking"
        elif entities.depth:
            return "profile_analysis"
        
        return "general_query"
    
    def _calculate_confidence(
        self,
        entities: ExtractedEntities,
        operators: List[Operator],
        intent: str
    ) -> float:
        """Calculate confidence score based on extraction quality."""
        scores = []
        
        # Entity extraction confidence
        all_entities = (
            entities.spatial + 
            entities.temporal + 
            entities.parameters +
            entities.floats +
            entities.quality +
            entities.depth
        )
        
        if all_entities:
            entity_confidence = sum(e.confidence for e in all_entities) / len(all_entities)
            scores.append(entity_confidence)
        else:
            scores.append(0.3)  # Low score if no entities extracted
        
        # Operator generation confidence
        if operators:
            # More operators generally means better understanding
            operator_score = min(1.0, len(operators) / 3)
            scores.append(operator_score)
        else:
            scores.append(0.2)
        
        # Intent detection confidence
        if intent != "general_query":
            scores.append(0.9)
        else:
            scores.append(0.5)
        
        # Average all scores
        return sum(scores) / len(scores) if scores else 0.0
    
    async def _generate_alternatives(
        self,
        query: str,
        doc: spacy.tokens.Doc,
        entities: ExtractedEntities
    ) -> List[SemanticOperatorDAG]:
        """Generate alternative interpretations for ambiguous queries."""
        alternatives = []
        
        # Alternative 1: Broaden spatial scope
        if entities.spatial:
            alt_entities = ExtractedEntities(
                spatial=[],  # Remove spatial constraint
                temporal=entities.temporal,
                parameters=entities.parameters,
                floats=entities.floats,
                quality=entities.quality,
                depth=entities.depth
            )
            ops, edges = await self.operator_generator.generate(
                entities=alt_entities,
                intent="global_analysis"
            )
            if ops:
                alternatives.append(SemanticOperatorDAG(
                    operators=ops,
                    edges=edges,
                    confidence=0.6,
                    intent="global_analysis",
                    entities=alt_entities.to_dict()
                ))
        
        # Alternative 2: Different parameter interpretation
        if entities.parameters:
            # Try with all common parameters
            from .domain_knowledge import COMMON_PARAMETERS
            alt_params = [
                type(entities.parameters[0])(
                    name=p["name"],
                    column=p["column"],
                    unit=p.get("unit"),
                    confidence=0.5
                )
                for p in COMMON_PARAMETERS[:3]
            ]
            alt_entities = ExtractedEntities(
                spatial=entities.spatial,
                temporal=entities.temporal,
                parameters=alt_params,
                floats=entities.floats,
                quality=entities.quality,
                depth=entities.depth
            )
            ops, edges = await self.operator_generator.generate(
                entities=alt_entities,
                intent="multi_parameter"
            )
            if ops:
                alternatives.append(SemanticOperatorDAG(
                    operators=ops,
                    edges=edges,
                    confidence=0.5,
                    intent="multi_parameter",
                    entities=alt_entities.to_dict()
                ))
        
        return alternatives[:3]  # Return top 3 alternatives
    
    async def _query_memory(
        self,
        query: str,
        entities: ExtractedEntities
    ) -> Optional[Dict[str, Any]]:
        """Query memory system for similar past queries."""
        if not self.memory:
            return None
        
        # TODO: Implement memory query when memory system is initialized
        return None
