"""Tests for SubscriptionManager - the orchestration layer for subscriptions"""
import pytest
from unittest.mock import AsyncMock, Mock, call
from app.stocks.subscription_manager import SubscriptionManager


class TestSubscriptionManager:
    """Test suite for SubscriptionManager"""

    @pytest.fixture
    def mock_websocket_subscribe(self):
        """Mock WebSocketManager.subscribe callback"""
        return AsyncMock(return_value=True)

    @pytest.fixture
    def mock_websocket_unsubscribe(self):
        """Mock WebSocketManager.unsubscribe callback"""
        return AsyncMock(return_value=True)

    @pytest.fixture
    def mock_handler_create(self):
        """Mock TradeDataAggregator.ensure_handler_exists callback"""
        return AsyncMock()

    @pytest.fixture
    def subscription_manager(self, mock_websocket_subscribe, mock_websocket_unsubscribe, mock_handler_create):
        """Create SubscriptionManager with mock callbacks"""
        return SubscriptionManager(
            subscribe_callback=mock_websocket_subscribe,
            unsubscribe_callback=mock_websocket_unsubscribe,
            on_handler_create_callback=mock_handler_create
        )

    def test_initialization(self, subscription_manager):
        """Test SubscriptionManager initializes correctly"""
        assert subscription_manager.user_subscriptions == {}
        assert subscription_manager.subscribe_callback is not None
        assert subscription_manager.unsubscribe_callback is not None
        assert subscription_manager.on_handler_create_callback is not None

    def test_initialization_without_callbacks(self):
        """Test initialization without callbacks"""
        manager = SubscriptionManager()
        assert manager.user_subscriptions == {}
        assert manager.subscribe_callback is None
        assert manager.unsubscribe_callback is None
        assert manager.on_handler_create_callback is None

    @pytest.mark.asyncio
    async def test_add_user_subscription_calls_handler_create_first(
        self, subscription_manager, mock_handler_create, mock_websocket_subscribe
    ):
        """Test that handler creation is called before websocket subscription"""
        await subscription_manager.add_user_subscription(user_id=1, symbol="AAPL", subscription_type="trades")

        # Both should be called
        mock_handler_create.assert_called_once_with("AAPL")
        mock_websocket_subscribe.assert_called_once_with("AAPL", 1, "trades")

        # Verify order: handler create happens first
        assert mock_handler_create.call_count == 1
        assert mock_websocket_subscribe.call_count == 1

    @pytest.mark.asyncio
    async def test_add_user_subscription_success(self, subscription_manager):
        """Test successful subscription adds to tracking"""
        result = await subscription_manager.add_user_subscription(
            user_id=123, symbol="AAPL", subscription_type="trades"
        )

        assert result is True
        assert 123 in subscription_manager.user_subscriptions
        assert ("AAPL", "trades") in subscription_manager.user_subscriptions[123]

    @pytest.mark.asyncio
    async def test_add_user_subscription_uppercases_symbol(self, subscription_manager, mock_handler_create, mock_websocket_subscribe):
        """Test that symbols are converted to uppercase"""
        await subscription_manager.add_user_subscription(user_id=1, symbol="aapl")

        # Both callbacks should receive uppercase symbol
        mock_handler_create.assert_called_once_with("AAPL")
        mock_websocket_subscribe.assert_called_once_with("AAPL", 1, "trades")

    @pytest.mark.asyncio
    async def test_add_multiple_subscriptions_same_user(self, subscription_manager):
        """Test adding multiple subscriptions for same user"""
        await subscription_manager.add_user_subscription(123, "AAPL")
        await subscription_manager.add_user_subscription(123, "GOOGL")
        await subscription_manager.add_user_subscription(123, "MSFT")

        assert len(subscription_manager.user_subscriptions[123]) == 3
        assert ("AAPL", "trades") in subscription_manager.user_subscriptions[123]
        assert ("GOOGL", "trades") in subscription_manager.user_subscriptions[123]
        assert ("MSFT", "trades") in subscription_manager.user_subscriptions[123]

    @pytest.mark.asyncio
    async def test_add_subscription_multiple_users_same_symbol(self, subscription_manager):
        """Test multiple users subscribing to same symbol"""
        await subscription_manager.add_user_subscription(1, "AAPL")
        await subscription_manager.add_user_subscription(2, "AAPL")
        await subscription_manager.add_user_subscription(3, "AAPL")

        assert len(subscription_manager.user_subscriptions) == 3
        assert all(("AAPL", "trades") in subs for subs in subscription_manager.user_subscriptions.values())

    @pytest.mark.asyncio
    async def test_add_subscription_different_types(self, subscription_manager):
        """Test subscribing to same symbol with different types"""
        await subscription_manager.add_user_subscription(1, "AAPL", "trades")
        await subscription_manager.add_user_subscription(1, "AAPL", "quotes")
        await subscription_manager.add_user_subscription(1, "AAPL", "bars")

        assert len(subscription_manager.user_subscriptions[1]) == 3
        assert ("AAPL", "trades") in subscription_manager.user_subscriptions[1]
        assert ("AAPL", "quotes") in subscription_manager.user_subscriptions[1]
        assert ("AAPL", "bars") in subscription_manager.user_subscriptions[1]

    @pytest.mark.asyncio
    async def test_add_subscription_handler_create_fails_continues(
        self, mock_websocket_subscribe, mock_websocket_unsubscribe
    ):
        """Test that subscription continues even if handler creation fails"""
        failing_handler_create = AsyncMock(side_effect=Exception("Handler creation failed"))

        manager = SubscriptionManager(
            subscribe_callback=mock_websocket_subscribe,
            unsubscribe_callback=mock_websocket_unsubscribe,
            on_handler_create_callback=failing_handler_create
        )

        result = await manager.add_user_subscription(1, "AAPL")

        # Should still succeed (websocket subscription)
        assert result is True
        failing_handler_create.assert_called_once()
        mock_websocket_subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_subscription_websocket_fails(self, subscription_manager, mock_websocket_subscribe):
        """Test handling of websocket subscription failure"""
        mock_websocket_subscribe.return_value = False

        result = await subscription_manager.add_user_subscription(1, "AAPL")

        assert result is False
        # Should not be added to tracking
        assert 1 not in subscription_manager.user_subscriptions

    @pytest.mark.asyncio
    async def test_remove_user_subscription(self, subscription_manager):
        """Test removing a subscription"""
        # First add a subscription
        await subscription_manager.add_user_subscription(123, "AAPL")
        assert ("AAPL", "trades") in subscription_manager.user_subscriptions[123]

        # Remove it
        result = await subscription_manager.remove_user_subscription(123, "AAPL")

        assert result is True
        # Should be removed from tracking
        assert 123 not in subscription_manager.user_subscriptions

    @pytest.mark.asyncio
    async def test_remove_subscription_keeps_other_symbols(self, subscription_manager):
        """Test removing one subscription keeps others"""
        await subscription_manager.add_user_subscription(123, "AAPL")
        await subscription_manager.add_user_subscription(123, "GOOGL")
        await subscription_manager.add_user_subscription(123, "MSFT")

        await subscription_manager.remove_user_subscription(123, "GOOGL")

        assert len(subscription_manager.user_subscriptions[123]) == 2
        assert ("AAPL", "trades") in subscription_manager.user_subscriptions[123]
        assert ("MSFT", "trades") in subscription_manager.user_subscriptions[123]
        assert ("GOOGL", "trades") not in subscription_manager.user_subscriptions[123]

    @pytest.mark.asyncio
    async def test_remove_nonexistent_subscription(self, subscription_manager, mock_websocket_unsubscribe):
        """Test removing subscription that doesn't exist"""
        result = await subscription_manager.remove_user_subscription(999, "FAKE")

        # Should still call unsubscribe callback
        mock_websocket_unsubscribe.assert_called_once_with("FAKE", 999, "trades")
        assert result is True

    def test_get_user_subscriptions_empty(self, subscription_manager):
        """Test getting subscriptions for user with none"""
        subs = subscription_manager.get_user_subscriptions(999)
        assert subs == set()

    @pytest.mark.asyncio
    async def test_get_user_subscriptions(self, subscription_manager):
        """Test getting user subscriptions"""
        await subscription_manager.add_user_subscription(1, "AAPL")
        await subscription_manager.add_user_subscription(1, "GOOGL", "quotes")

        subs = subscription_manager.get_user_subscriptions(1)

        assert len(subs) == 2
        assert ("AAPL", "trades") in subs
        assert ("GOOGL", "quotes") in subs

    def test_get_user_symbols_all_types(self, subscription_manager):
        """Test getting just symbols (all types)"""
        subscription_manager.user_subscriptions[1] = {
            ("AAPL", "trades"),
            ("GOOGL", "quotes"),
            ("MSFT", "bars")
        }

        symbols = subscription_manager.get_user_symbols(1)

        assert len(symbols) == 3
        assert symbols == {"AAPL", "GOOGL", "MSFT"}

    def test_get_user_symbols_filtered_by_type(self, subscription_manager):
        """Test getting symbols filtered by subscription type"""
        subscription_manager.user_subscriptions[1] = {
            ("AAPL", "trades"),
            ("GOOGL", "trades"),
            ("MSFT", "quotes"),
            ("TSLA", "bars")
        }

        trade_symbols = subscription_manager.get_user_symbols(1, subscription_type="trades")

        assert len(trade_symbols) == 2
        assert trade_symbols == {"AAPL", "GOOGL"}

    def test_get_all_subscriptions(self, subscription_manager):
        """Test getting all subscriptions across all users"""
        subscription_manager.user_subscriptions = {
            1: {("AAPL", "trades"), ("GOOGL", "quotes")},
            2: {("MSFT", "trades")},
            3: {("TSLA", "bars")}
        }

        all_subs = subscription_manager.get_all_subscriptions()

        assert len(all_subs) == 3
        assert 1 in all_subs
        assert 2 in all_subs
        assert 3 in all_subs
        # Should be a copy, not original
        assert all_subs is not subscription_manager.user_subscriptions


@pytest.mark.asyncio
async def test_subscription_manager_integration_flow():
    """Integration test of full subscription/unsubscription flow"""
    # Track call order
    call_order = []

    async def mock_handler_create(symbol):
        call_order.append(f"handler_create:{symbol}")

    async def mock_ws_subscribe(symbol, user_id, sub_type):
        call_order.append(f"ws_subscribe:{symbol}:{user_id}:{sub_type}")
        return True

    async def mock_ws_unsubscribe(symbol, user_id, sub_type):
        call_order.append(f"ws_unsubscribe:{symbol}:{user_id}:{sub_type}")
        return True

    manager = SubscriptionManager(
        subscribe_callback=mock_ws_subscribe,
        unsubscribe_callback=mock_ws_unsubscribe,
        on_handler_create_callback=mock_handler_create
    )

    # Add subscription
    result = await manager.add_user_subscription(123, "AAPL", "trades")
    assert result is True

    # Verify call order
    assert call_order[0] == "handler_create:AAPL"
    assert call_order[1] == "ws_subscribe:AAPL:123:trades"

    # Verify tracking
    assert ("AAPL", "trades") in manager.user_subscriptions[123]

    # Remove subscription
    call_order.clear()
    result = await manager.remove_user_subscription(123, "AAPL", "trades")
    assert result is True

    assert call_order[0] == "ws_unsubscribe:AAPL:123:trades"

    # Verify removed from tracking
    assert 123 not in manager.user_subscriptions


@pytest.mark.asyncio
async def test_concurrent_subscriptions():
    """Test handling concurrent subscriptions from multiple users"""
    mock_handler_create = AsyncMock()
    mock_ws_subscribe = AsyncMock(return_value=True)

    manager = SubscriptionManager(
        subscribe_callback=mock_ws_subscribe,
        on_handler_create_callback=mock_handler_create
    )

    # Simulate multiple users subscribing concurrently
    import asyncio
    tasks = [
        manager.add_user_subscription(1, "AAPL"),
        manager.add_user_subscription(2, "AAPL"),
        manager.add_user_subscription(3, "GOOGL"),
        manager.add_user_subscription(1, "MSFT"),
    ]

    results = await asyncio.gather(*tasks)

    # All should succeed
    assert all(results)

    # Verify all users tracked
    assert len(manager.user_subscriptions) == 3
    assert ("AAPL", "trades") in manager.user_subscriptions[1]
    assert ("MSFT", "trades") in manager.user_subscriptions[1]
    assert ("AAPL", "trades") in manager.user_subscriptions[2]
    assert ("GOOGL", "trades") in manager.user_subscriptions[3]
