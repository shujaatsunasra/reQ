"""
Tests for NL2Operator pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from nl2op import NL2Operator, EntityExtractor, OperatorGenerator
from models.operators import SemanticOperatorDAG, OperatorType


class TestEntityExtractor:
    """Tests for entity extraction."""
    
    @pytest.fixture
    def extractor(self):
        return EntityExtractor()
        
    def test_extract_region_arabian_sea(self, extractor):
        """Should extract Arabian Sea region."""
        entities = extractor.extract("Show data from the Arabian Sea")
        
        regions = [e for e in entities if e.type == "region"]
        assert len(regions) == 1
        assert regions[0].value == "arabian_sea"
        assert regions[0].bounds is not None
        
    def test_extract_multiple_regions(self, extractor):
        """Should extract multiple regions."""
        entities = extractor.extract("Compare Bay of Bengal with Indian Ocean")
        
        regions = [e for e in entities if e.type == "region"]
        assert len(regions) == 2
        
    def test_extract_temporal_relative(self, extractor):
        """Should extract relative time expressions."""
        entities = extractor.extract("Data from last month")
        
        temporal = [e for e in entities if e.type == "temporal"]
        assert len(temporal) == 1
        assert temporal[0].value == "last_month"
        
    def test_extract_temporal_range(self, extractor):
        """Should extract date ranges."""
        entities = extractor.extract("Between January 2024 and March 2024")
        
        temporal = [e for e in entities if e.type == "temporal"]
        assert len(temporal) >= 1
        
    def test_extract_depth(self, extractor):
        """Should extract depth values."""
        entities = extractor.extract("At 500 meters depth")
        
        depths = [e for e in entities if e.type == "depth"]
        assert len(depths) == 1
        assert depths[0].value == 500
        
    def test_extract_depth_range(self, extractor):
        """Should extract depth ranges."""
        entities = extractor.extract("Between 200 and 1000 dbar")
        
        depths = [e for e in entities if e.type == "depth"]
        assert len(depths) == 1
        assert depths[0].range == [200, 1000]
        
    def test_extract_parameters(self, extractor):
        """Should extract oceanographic parameters."""
        entities = extractor.extract("Show temperature and salinity")
        
        params = [e for e in entities if e.type == "parameter"]
        assert len(params) == 2
        assert "temperature" in [p.value for p in params]
        assert "salinity" in [p.value for p in params]
        
    def test_extract_float_id(self, extractor):
        """Should extract float WMO IDs."""
        entities = extractor.extract("Data from float 6901234")
        
        floats = [e for e in entities if e.type == "float_id"]
        assert len(floats) == 1
        assert floats[0].value == "6901234"
        

class TestOperatorGenerator:
    """Tests for operator generation."""
    
    @pytest.fixture
    def generator(self):
        return OperatorGenerator()
        
    @pytest.mark.asyncio
    async def test_generate_spatial_filter(self, generator):
        """Should generate spatial filter operator."""
        from models.entities import Entity
        
        entities = [
            Entity(type="region", value="arabian_sea", 
                   bounds={"lat": [5, 25], "lon": [50, 80]})
        ]
        
        operators = await generator.generate(
            query="Data from Arabian Sea",
            entities=entities,
            intent="retrieve_data"
        )
        
        spatial_ops = [op for op in operators if op.type == OperatorType.SPATIAL_FILTER]
        assert len(spatial_ops) == 1
        
    @pytest.mark.asyncio
    async def test_generate_visualization(self, generator):
        """Should generate visualization operator for trajectory request."""
        from models.entities import Entity
        
        entities = [
            Entity(type="region", value="arabian_sea",
                   bounds={"lat": [5, 25], "lon": [50, 80]})
        ]
        
        operators = await generator.generate(
            query="Show float trajectories in Arabian Sea",
            entities=entities,
            intent="visualize"
        )
        
        viz_ops = [op for op in operators if op.type == OperatorType.VISUALIZATION]
        assert len(viz_ops) >= 1
        assert viz_ops[0].config.get("viz_type") == "trajectory_map"


class TestNL2Operator:
    """Integration tests for the full NL2Operator pipeline."""
    
    @pytest.fixture
    def nl2op(self):
        return NL2Operator()
        
    @pytest.mark.asyncio
    async def test_parse_simple_query(self, nl2op):
        """Should parse a simple data retrieval query."""
        dag = await nl2op.parse(
            query="Show temperature in the Arabian Sea",
            mode="explorer"
        )
        
        assert isinstance(dag, SemanticOperatorDAG)
        assert dag.confidence > 0.5
        assert len(dag.operators) >= 1
        
    @pytest.mark.asyncio
    async def test_parse_complex_query(self, nl2op):
        """Should parse a complex analytical query."""
        dag = await nl2op.parse(
            query="Calculate mixed layer depth anomalies in the Bay of Bengal for the last 6 months",
            mode="power"
        )
        
        assert dag.confidence > 0.5
        
        # Should have multiple operators
        operator_types = [op.type for op in dag.operators]
        assert OperatorType.TEMPORAL_FILTER in operator_types
        assert OperatorType.SPATIAL_FILTER in operator_types
        
    @pytest.mark.asyncio
    async def test_parse_ambiguous_query(self, nl2op):
        """Should generate alternatives for ambiguous query."""
        dag = await nl2op.parse(
            query="What's the data?",
            mode="explorer"
        )
        
        # Low confidence or alternatives
        assert dag.confidence < 0.8 or len(dag.alternatives) > 0
        
    @pytest.mark.asyncio
    async def test_context_awareness(self, nl2op):
        """Should use context from previous queries."""
        # First query establishes context
        dag1 = await nl2op.parse(
            query="Show temperature in the Arabian Sea",
            mode="explorer"
        )
        
        # Second query should use previous context
        dag2 = await nl2op.parse(
            query="Now show salinity instead",
            mode="explorer",
            context={
                "previous_query": "Show temperature in the Arabian Sea",
                "previous_region": "arabian_sea"
            }
        )
        
        # Should still have Arabian Sea filter
        spatial_ops = [op for op in dag2.operators 
                       if op.type == OperatorType.SPATIAL_FILTER]
        assert len(spatial_ops) >= 1
