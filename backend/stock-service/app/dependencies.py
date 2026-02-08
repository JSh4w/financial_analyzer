"""FastAPI dependency injection functions for accessing application state."""

from app.database.external_database_manager import DatabaseManager
from app.database.stock_data_manager import StockDataManager
from app.database.subscription_manager import PersistentSubscriptionManager
from app.services.gocardless import GoCardlessClient
from app.stocks.data_aggregator import TradeDataAggregator
from app.stocks.subscription_manager import SubscriptionManager
from app.stocks.websocket_manager import WebSocketManager
from fastapi import Request
from snaptrade_client import SnapTrade


# Dependency injection functions
def get_ws_manager(request: Request) -> WebSocketManager:
    """Get WebSocket manager from state"""
    return request.state.ws_manager


def get_demo_ws_manager(request: Request) -> WebSocketManager:
    """Get demo WebSocket manager from state"""
    return request.state.demo_ws_manager


def get_data_aggregator(request: Request) -> TradeDataAggregator:
    """Get data aggregator from state"""
    return request.state.data_aggregator


def get_db_manager(request: Request) -> StockDataManager:
    """Get database manager from state"""
    return request.state.db_manager


def get_subscription_manager(request: Request) -> SubscriptionManager:
    """Get subscription manager from state"""
    return request.state.subscription_manager


def get_demo_subscription_manager(request: Request) -> SubscriptionManager:
    """Get demo subscription manager from state"""
    return request.state.demo_subscription_manager


def get_banking_client(request: Request) -> GoCardlessClient:
    """Get GoCardless client from state"""
    return request.state.banking_client


def get_supabase_db(request: Request) -> DatabaseManager:
    """Get Supabase database manager from state"""
    return request.state.supabase_db


def get_persistent_subscription_manager(
    request: Request,
) -> PersistentSubscriptionManager:
    """Get persistent subscription manager from state"""
    return request.state.persistent_subscription_manager


def get_brokerage_client(request: Request) -> SnapTrade:
    """Get Snaptrade instance from state"""
    return request.state.brokerage_client
