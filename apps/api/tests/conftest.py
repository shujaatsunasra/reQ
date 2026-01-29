"""
Tests configuration and fixtures.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database():
    """Mock database connection pool."""
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock()
    pool.acquire.return_value.__aexit__ = AsyncMock()
    return pool


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    client = MagicMock()
    collection = MagicMock()
    collection.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]]
    }
    client.get_collection.return_value = collection
    return client


@pytest.fixture
def sample_profile_data():
    """Sample ARGO profile data for testing."""
    return {
        "float_id": "6901234",
        "cycle_number": 42,
        "timestamp": "2024-01-15T12:00:00Z",
        "latitude": 15.5,
        "longitude": 65.3,
        "pressure": [5, 10, 20, 50, 100, 200, 500, 1000, 2000],
        "temperature": [29.0, 28.8, 28.5, 26.0, 20.0, 14.0, 8.0, 5.0, 2.5],
        "salinity": [34.8, 34.9, 35.0, 35.1, 35.2, 35.3, 35.4, 35.5, 35.6],
        "pressure_qc": [1, 1, 1, 1, 1, 1, 1, 1, 1],
        "temperature_qc": [1, 1, 1, 1, 1, 1, 1, 1, 1],
        "salinity_qc": [1, 1, 1, 1, 1, 1, 1, 1, 1]
    }


@pytest.fixture
def sample_trajectory_data():
    """Sample float trajectory data for testing."""
    return {
        "float_id": "6901234",
        "positions": [
            {"lat": 15.0, "lon": 65.0, "timestamp": "2024-01-01T00:00:00Z", "cycle": 40},
            {"lat": 15.2, "lon": 65.1, "timestamp": "2024-01-11T00:00:00Z", "cycle": 41},
            {"lat": 15.5, "lon": 65.3, "timestamp": "2024-01-21T00:00:00Z", "cycle": 42},
        ]
    }


@pytest.fixture
def sample_region():
    """Sample ocean region definition."""
    return {
        "name": "arabian_sea",
        "display_name": "Arabian Sea",
        "bounds": {
            "lat": [5, 25],
            "lon": [50, 80]
        }
    }
