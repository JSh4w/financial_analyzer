"""Pytest configuration and shared fixtures"""
import logging
import sys
import os
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user_id
from app.database.stock_data_manager import StockDataManager
from app.database.connection import DuckDBConnection
from app.main import app

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
    return "2022-01-01T00:00:00Z"

@pytest.fixture
def temp_db_path():
    """Create temporary database path for testing"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_stock_data.duckdb")
    yield db_path
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

@pytest.fixture
def db_manager(temp_db_path):
    """Create StockDataManager instance for testing"""
    db_connection = DuckDBConnection(db_path=temp_db_path)
    manager = StockDataManager(db_connection=db_connection)
    yield manager
    manager.close()

@pytest.fixture
def client(db_manager):
    """Create FastAPI test client with database"""
    # Import here to avoid circular dependency
    from app.dependencies import get_db_manager

    async def fake_user():
        return "test-user-id"

    def override_db_manager():
        return db_manager

    app.dependency_overrides[get_current_user_id] = fake_user
    app.dependency_overrides[get_db_manager] = override_db_manager

    # Set the global database manager for the app
    app.state.db_manager = db_manager

    yield TestClient(app)

    # Cleanup
    app.state.db_manager = None
    app.dependency_overrides.clear()
