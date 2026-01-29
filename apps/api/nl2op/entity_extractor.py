"""
Entity extraction from natural language queries.
Extracts spatial, temporal, parameter, and other oceanographic entities.
"""

import re
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
import spacy
from spacy.language import Language

from core.logging import get_logger
from models.entities import (
    ExtractedEntities,
    SpatialEntity,
    TemporalEntity,
    ParameterEntity,
    FloatEntity,
    QualityEntity,
    DepthEntity
)
from .domain_knowledge import (
    OCEAN_REGIONS,
    OCEANOGRAPHIC_PARAMETERS,
    QC_MAPPINGS,
    DEPTH_PATTERNS
)

logger = get_logger(__name__)


class EntityExtractor:
    """
    Extracts oceanographic entities from natural language queries.
    
    Uses spaCy NER combined with domain-specific pattern matching
    for ocean regions, parameters, and quality flags.
    """
    
    def __init__(self, nlp: Language):
        self.nlp = nlp
    
    async def extract(
        self,
        doc: spacy.tokens.Doc,
        query: str
    ) -> ExtractedEntities:
        """
        Extract all entity types from a parsed document.
        
        Args:
            doc: spaCy parsed document
            query: Original query string
        
        Returns:
            ExtractedEntities with all extracted entities
        """
        return ExtractedEntities(
            spatial=await self._extract_spatial(doc, query),
            temporal=await self._extract_temporal(doc, query),
            parameters=await self._extract_parameters(doc, query),
            floats=await self._extract_floats(doc, query),
            quality=await self._extract_quality(doc, query),
            depth=await self._extract_depth(doc, query)
        )
    
    async def _extract_spatial(
        self,
        doc: spacy.tokens.Doc,
        query: str
    ) -> List[SpatialEntity]:
        """Extract spatial/geographic entities."""
        entities = []
        query_lower = query.lower()
        
        # Check for known ocean regions
        for region_name, region_data in OCEAN_REGIONS.items():
            if region_name.lower() in query_lower:
                entities.append(SpatialEntity(
                    name=region_name,
                    type="region",
                    bbox=tuple(region_data["bbox"]),
                    center=tuple(region_data.get("center", [
                        (region_data["bbox"][0] + region_data["bbox"][2]) / 2,
                        (region_data["bbox"][1] + region_data["bbox"][3]) / 2
                    ])),
                    confidence=0.95
                ))
        
        # Check for spaCy GPE (Geo-Political Entity) and LOC entities
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                # Check if it's a known region
                ent_lower = ent.text.lower()
                matched = False
                for region_name in OCEAN_REGIONS:
                    if ent_lower in region_name.lower() or region_name.lower() in ent_lower:
                        matched = True
                        break
                
                if not matched:
                    # Unknown location - try to geocode or use as-is
                    entities.append(SpatialEntity(
                        name=ent.text,
                        type="location",
                        confidence=0.6
                    ))
        
        # Extract coordinate patterns (e.g., "near 10°N, 50°E")
        coord_pattern = r'(-?\d+(?:\.\d+)?)\s*°?\s*([NS])[,\s]+(-?\d+(?:\.\d+)?)\s*°?\s*([EW])'
        for match in re.finditer(coord_pattern, query, re.IGNORECASE):
            lat = float(match.group(1))
            if match.group(2).upper() == 'S':
                lat = -lat
            lon = float(match.group(3))
            if match.group(4).upper() == 'W':
                lon = -lon
            
            # Create a small bounding box around the point
            entities.append(SpatialEntity(
                name=f"({lat}°, {lon}°)",
                type="point",
                center=(lon, lat),
                bbox=(lon - 1, lat - 1, lon + 1, lat + 1),
                confidence=0.9
            ))
        
        # Extract "equator" specifically
        if "equator" in query_lower:
            entities.append(SpatialEntity(
                name="Equator",
                type="region",
                bbox=(-180, -5, 180, 5),
                center=(0, 0),
                confidence=0.95
            ))
        
        return entities
    
    async def _extract_temporal(
        self,
        doc: spacy.tokens.Doc,
        query: str
    ) -> List[TemporalEntity]:
        """Extract temporal entities."""
        entities = []
        query_lower = query.lower()
        now = datetime.now()
        
        # Relative time patterns
        relative_patterns = [
            (r"last\s+(\d+)?\s*month", lambda m: (
                now - relativedelta(months=int(m.group(1) or 1)),
                now,
                "relative"
            )),
            (r"last\s+(\d+)?\s*year", lambda m: (
                now - relativedelta(years=int(m.group(1) or 1)),
                now,
                "relative"
            )),
            (r"last\s+(\d+)?\s*week", lambda m: (
                now - timedelta(weeks=int(m.group(1) or 1)),
                now,
                "relative"
            )),
            (r"last\s+(\d+)?\s*day", lambda m: (
                now - timedelta(days=int(m.group(1) or 1)),
                now,
                "relative"
            )),
            (r"past\s+(\d+)?\s*month", lambda m: (
                now - relativedelta(months=int(m.group(1) or 1)),
                now,
                "relative"
            )),
            (r"this\s+month", lambda m: (
                now.replace(day=1),
                now,
                "relative"
            )),
            (r"this\s+year", lambda m: (
                now.replace(month=1, day=1),
                now,
                "relative"
            )),
        ]
        
        for pattern, handler in relative_patterns:
            match = re.search(pattern, query_lower)
            if match:
                start, end, type_ = handler(match)
                entities.append(TemporalEntity(
                    text=match.group(0),
                    type=type_,
                    start=start,
                    end=end,
                    confidence=0.9
                ))
        
        # Season patterns
        seasons = {
            "winter": (12, 2),
            "spring": (3, 5),
            "summer": (6, 8),
            "fall": (9, 11),
            "autumn": (9, 11)
        }
        
        for season, (start_month, end_month) in seasons.items():
            if season in query_lower:
                # Check for year
                year_match = re.search(r'(\d{4})', query)
                year = int(year_match.group(1)) if year_match else now.year
                
                if start_month > end_month:  # Winter spans year boundary
                    start = datetime(year - 1, start_month, 1)
                    end = datetime(year, end_month, 28)
                else:
                    start = datetime(year, start_month, 1)
                    end = datetime(year, end_month, 28)
                
                entities.append(TemporalEntity(
                    text=f"{season} {year}",
                    type="season",
                    start=start,
                    end=end,
                    confidence=0.85
                ))
        
        # Specific date patterns (e.g., "March 2019", "2023-01-15")
        for ent in doc.ents:
            if ent.label_ == "DATE":
                try:
                    parsed = date_parser.parse(ent.text, fuzzy=True)
                    # Determine if it's a full date or partial
                    if re.search(r'\d{4}-\d{2}-\d{2}', ent.text):
                        # Full date
                        entities.append(TemporalEntity(
                            text=ent.text,
                            type="absolute",
                            start=parsed,
                            end=parsed + timedelta(days=1),
                            confidence=0.95
                        ))
                    elif re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}', ent.text.lower()):
                        # Month + year
                        start = parsed.replace(day=1)
                        end = start + relativedelta(months=1)
                        entities.append(TemporalEntity(
                            text=ent.text,
                            type="month",
                            start=start,
                            end=end,
                            confidence=0.9
                        ))
                    elif re.search(r'\d{4}', ent.text):
                        # Just year
                        year = int(re.search(r'\d{4}', ent.text).group(0))
                        entities.append(TemporalEntity(
                            text=ent.text,
                            type="year",
                            start=datetime(year, 1, 1),
                            end=datetime(year, 12, 31),
                            confidence=0.85
                        ))
                except:
                    pass
        
        return entities
    
    async def _extract_parameters(
        self,
        doc: spacy.tokens.Doc,
        query: str
    ) -> List[ParameterEntity]:
        """Extract oceanographic parameter entities."""
        entities = []
        query_lower = query.lower()
        
        for param_name, param_data in OCEANOGRAPHIC_PARAMETERS.items():
            # Check main name and aliases
            names_to_check = [param_name.lower()] + [a.lower() for a in param_data.get("aliases", [])]
            
            for name in names_to_check:
                if name in query_lower:
                    entities.append(ParameterEntity(
                        name=param_name,
                        column=param_data["column"],
                        unit=param_data.get("unit"),
                        confidence=0.95
                    ))
                    break  # Only add once per parameter
        
        return entities
    
    async def _extract_floats(
        self,
        doc: spacy.tokens.Doc,
        query: str
    ) -> List[FloatEntity]:
        """Extract ARGO float identifiers."""
        entities = []
        
        # Float ID patterns (7-digit numbers, or with prefix)
        float_patterns = [
            r'float\s+(?:id\s+)?(\d{7})',
            r'platform\s+(\d{7})',
            r'\b(\d{7})\b',  # Standalone 7-digit number
            r'#(\d{7})',
        ]
        
        for pattern in float_patterns:
            for match in re.finditer(pattern, query, re.IGNORECASE):
                float_id = match.group(1)
                entities.append(FloatEntity(
                    text=match.group(0),
                    float_id=float_id,
                    confidence=0.9
                ))
        
        return entities
    
    async def _extract_quality(
        self,
        doc: spacy.tokens.Doc,
        query: str
    ) -> List[QualityEntity]:
        """Extract quality control entities."""
        entities = []
        query_lower = query.lower()
        
        for qc_term, qc_data in QC_MAPPINGS.items():
            if qc_term in query_lower:
                entities.append(QualityEntity(
                    text=qc_term,
                    qc_flags=qc_data["flags"],
                    data_mode=qc_data.get("data_mode"),
                    confidence=0.9
                ))
        
        # Check for data mode
        if "real-time" in query_lower or "realtime" in query_lower:
            entities.append(QualityEntity(
                text="real-time",
                qc_flags=[],
                data_mode="R",
                confidence=0.9
            ))
        elif "delayed" in query_lower or "delayed-mode" in query_lower:
            entities.append(QualityEntity(
                text="delayed-mode",
                qc_flags=[],
                data_mode="D",
                confidence=0.9
            ))
        elif "adjusted" in query_lower:
            entities.append(QualityEntity(
                text="adjusted",
                qc_flags=[],
                data_mode="A",
                confidence=0.9
            ))
        
        return entities
    
    async def _extract_depth(
        self,
        doc: spacy.tokens.Doc,
        query: str
    ) -> List[DepthEntity]:
        """Extract depth/pressure entities."""
        entities = []
        query_lower = query.lower()
        
        for pattern, handler in DEPTH_PATTERNS:
            match = re.search(pattern, query_lower)
            if match:
                result = handler(match)
                entities.append(DepthEntity(
                    text=match.group(0),
                    min_depth=result.get("min"),
                    max_depth=result.get("max"),
                    confidence=0.9
                ))
        
        return entities
