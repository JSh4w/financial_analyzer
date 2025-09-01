"""Pytest configuration and shared fixtures"""
import logging
import sys
from pathlib import Path
import pytest
# Add the backend directory to Python path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

@pytest.fixture
def sample_symbols():
    """Common symbols for testing"""
    return ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]

@pytest.fixture
def base_timestamp():
    """Base timestamp for consistent testing (2022-01-01 00:00:00 UTC)"""
    return 1640995200000
