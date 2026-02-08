"""Test SnapTrade API endpoints"""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user_id
from app.dependencies import get_brokerage_client, get_supabase_db
from app.main import app


@pytest.fixture
def mock_snaptrade_client():
    """Create a mock SnapTrade client"""
    client = MagicMock()

    # Mock register response
    register_response = MagicMock()
    register_response.body = {"userSecret": "test-secret-123"}
    client.authentication.register_snap_trade_user.return_value = register_response

    # Mock login response
    login_response = MagicMock()
    login_response.body = "https://app.snaptrade.com/connect?token=abc123"
    client.authentication.login_snap_trade_user.return_value = login_response

    # Mock holdings response
    holdings_response = MagicMock()
    holdings_response.body = [
        {
            "account": {"id": "acc-123", "name": "My Brokerage"},
            "balances": [{"currency": "USD", "cash": 1000.00}],
            "positions": [
                {"symbol": "AAPL", "units": 10, "price": 150.00}
            ],
        }
    ]
    client.account_information.get_all_user_holdings.return_value = holdings_response

    # Mock delete response
    delete_response = MagicMock()
    delete_response.body = {"status": "deleted", "userId": "test-user-id"}
    client.authentication.delete_snap_trade_user.return_value = delete_response

    return client


@pytest.fixture
def mock_db_manager():
    """Create a mock DatabaseManager for SnapTrade operations"""
    db = MagicMock()
    db.get_snaptrade_user_secret.return_value = "test-secret-123"
    db.store_snaptrade_user.return_value = True
    db.delete_snaptrade_user.return_value = True
    return db


@pytest.fixture
def snaptrade_client(mock_snaptrade_client, mock_db_manager):
    """Create FastAPI test client with mocked dependencies"""

    async def fake_user():
        return "test-user-id"

    def override_snaptrade():
        return mock_snaptrade_client

    def override_db():
        return mock_db_manager

    app.dependency_overrides[get_current_user_id] = fake_user
    app.dependency_overrides[get_brokerage_client] = override_snaptrade
    app.dependency_overrides[get_supabase_db] = override_db

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_register_user(snaptrade_client, mock_snaptrade_client, mock_db_manager):
    """Test user registration endpoint"""
    response = snaptrade_client.post("/brokerages/register")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "registered"
    assert data["user_id"] == "test-user-id"

    # Verify SnapTrade client was called
    mock_snaptrade_client.authentication.register_snap_trade_user.assert_called_once_with(
        body={"userId": "test-user-id"}
    )

    # Verify DB store was called
    mock_db_manager.store_snaptrade_user.assert_called_once_with(
        "test-user-id", "test-secret-123"
    )


def test_register_user_db_not_implemented(snaptrade_client, mock_db_manager):
    """Test registration when DB storage raises NotImplementedError"""
    mock_db_manager.store_snaptrade_user.side_effect = NotImplementedError()

    response = snaptrade_client.post("/brokerages/register")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "registered"
    assert "user_secret" in data  # Should return secret when DB not implemented


def test_get_login_url(snaptrade_client, mock_snaptrade_client):
    """Test login URL endpoint"""
    response = snaptrade_client.get("/brokerages/login_url")
    assert response.status_code == 200

    data = response.json()
    assert "redirect_url" in data
    assert "snaptrade.com" in data["redirect_url"]


def test_get_login_url_with_redirect(snaptrade_client, mock_snaptrade_client):
    """Test login URL endpoint with custom redirect"""
    response = snaptrade_client.get(
        "/brokerages/login_url?redirect_uri=https://myapp.com/callback"
    )
    assert response.status_code == 200

    # Verify custom redirect was passed
    call_args = mock_snaptrade_client.authentication.login_snap_trade_user.call_args
    assert call_args[1]["query_params"]["customRedirect"] == "https://myapp.com/callback"


def test_get_login_url_user_not_registered(snaptrade_client, mock_db_manager):
    """Test login URL when user is not registered"""
    mock_db_manager.get_snaptrade_user_secret.return_value = None

    response = snaptrade_client.get("/brokerages/login_url")
    assert response.status_code == 404
    assert "not registered" in response.json()["detail"]


def test_get_holdings(snaptrade_client, mock_snaptrade_client):
    """Test holdings endpoint"""
    response = snaptrade_client.get("/brokerages/holdings")
    assert response.status_code == 200

    data = response.json()
    assert "holdings" in data
    assert data["user_id"] == "test-user-id"
    assert len(data["holdings"]) > 0


def test_get_holdings_user_not_registered(snaptrade_client, mock_db_manager):
    """Test holdings when user is not registered"""
    mock_db_manager.get_snaptrade_user_secret.return_value = None

    response = snaptrade_client.get("/brokerages/holdings")
    assert response.status_code == 404
    assert "not registered" in response.json()["detail"]


def test_delete_user(snaptrade_client, mock_snaptrade_client, mock_db_manager):
    """Test user deletion endpoint"""
    response = snaptrade_client.delete("/brokerages/user")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "deleted"
    assert data["user_id"] == "test-user-id"

    # Verify SnapTrade delete was called
    mock_snaptrade_client.authentication.delete_snap_trade_user.assert_called_once()

    # Verify DB delete was called
    mock_db_manager.delete_snaptrade_user.assert_called_once_with("test-user-id")


def test_delete_user_db_not_implemented(snaptrade_client, mock_db_manager):
    """Test deletion when DB delete raises NotImplementedError"""
    mock_db_manager.delete_snaptrade_user.side_effect = NotImplementedError()

    response = snaptrade_client.delete("/brokerages/user")
    assert response.status_code == 200  # Should still succeed

    data = response.json()
    assert data["status"] == "deleted"


def test_register_http_error(snaptrade_client, mock_snaptrade_client):
    """Test registration when SnapTrade API returns error"""
    mock_response = MagicMock()
    mock_response.status_code = 400
    error = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=mock_response
    )
    mock_snaptrade_client.authentication.register_snap_trade_user.side_effect = error

    response = snaptrade_client.post("/brokerages/register")
    assert response.status_code == 400
    assert "Failed to register" in response.json()["detail"]


def test_holdings_http_error(snaptrade_client, mock_snaptrade_client):
    """Test holdings when SnapTrade API returns error"""
    mock_response = MagicMock()
    mock_response.status_code = 401
    error = httpx.HTTPStatusError(
        "Unauthorized", request=MagicMock(), response=mock_response
    )
    mock_snaptrade_client.account_information.get_all_user_holdings.side_effect = error

    response = snaptrade_client.get("/brokerages/holdings")
    assert response.status_code == 401
    assert "Failed to get holdings" in response.json()["detail"]
