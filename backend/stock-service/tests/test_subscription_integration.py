"""Integration tests for complete subscription flow
Tests the full flow: SubscriptionManager → WebSocketManager + TradeDataAggregator → StockHandler → SSE
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
from models.websocket_models import BarData, TradeData
from app.stocks.subscription_manager import SubscriptionManager
from app.stocks.websocket_manager import WebSocketManager
from app.stocks.data_aggregator import TradeDataAggregator
from app.stocks.historical_data import AlpacaHistoricalData


@pytest.mark.asyncio
async def test_full_subscription_flow_without_websocket():
    """Test complete subscription flow with mocked components"""
    # Track calls and data
    handler_create_calls = []
    ws_subscribe_calls = []
    historical_fetch_calls = []
    sse_broadcasts = []

    # Mock historical fetcher
    mock_historical_fetcher = Mock(spec=AlpacaHistoricalData)
    mock_historical_fetcher.fetch_historical_bars = AsyncMock(return_value=[
        BarData(
            T='b', S='AAPL', o=150.0, h=151.0, l=149.5, c=150.5,
            v=10000, t='2022-01-01T09:30:00Z', n=50, vw=150.25
        ),
        BarData(
            T='b', S='AAPL', o=150.5, h=152.0, l=150.0, c=151.5,
            v=12000, t='2022-01-01T09:31:00Z', n=60, vw=151.0
        )
    ])

    # Mock broadcast callback (SSE)
    def mock_broadcast(update_data):
        sse_broadcasts.append(update_data)

    # Create TradeDataAggregator
    shared_queue = asyncio.Queue(500)
    aggregator = TradeDataAggregator(
        input_queue=shared_queue,
        broadcast_callback=mock_broadcast,
        historical_fetcher=mock_historical_fetcher
    )

    # Mock WebSocket subscribe
    async def mock_ws_subscribe(symbol, user_id, subscription_type):
        ws_subscribe_calls.append((symbol, user_id, subscription_type))
        return True

    # Create SubscriptionManager
    subscription_manager = SubscriptionManager(
        subscribe_callback=mock_ws_subscribe,
        on_handler_create_callback=aggregator.ensure_handler_exists
    )

    # Execute subscription
    result = await subscription_manager.add_user_subscription(
        user_id=123,
        symbol="AAPL",
        subscription_type="trades"
    )

    # Verify subscription succeeded
    assert result is True

    # Wait for historical data to load
    await asyncio.sleep(0.2)

    # Verify flow
    assert len(ws_subscribe_calls) == 1
    assert ws_subscribe_calls[0] == ("AAPL", 123, "trades")

    # Verify handler was created
    assert 'AAPL' in aggregator.stock_handlers

    # Verify historical fetch was called
    mock_historical_fetcher.fetch_historical_bars.assert_called_once()

    # Verify SSE broadcast happened (historical load)
    await asyncio.sleep(0.2)
    # Should have broadcast historical data
    assert len(sse_broadcasts) > 0


@pytest.mark.asyncio
async def test_subscription_flow_with_live_data_processing():
    """Test subscription flow with simulated live data"""
    sse_broadcasts = []

    def mock_broadcast(update_data):
        sse_broadcasts.append(update_data)

    # Create components
    shared_queue = asyncio.Queue(500)
    aggregator = TradeDataAggregator(
        input_queue=shared_queue,
        broadcast_callback=mock_broadcast
    )

    # Create subscription manager
    subscription_manager = SubscriptionManager(
        subscribe_callback=AsyncMock(return_value=True),
        on_handler_create_callback=aggregator.ensure_handler_exists
    )

    # Subscribe to symbol
    await subscription_manager.add_user_subscription(123, "AAPL")

    # Verify handler created
    assert 'AAPL' in aggregator.stock_handlers

    # Simulate live trade data arriving
    trade_data = TradeData(
        T='t', S='AAPL', i=1, x='V', p=150.0, s=100,
        c=[], t='2022-01-01T09:30:15Z', z='A'
    )

    # Queue the trade
    await shared_queue.put(trade_data)

    # Process the trade manually (simulating process_tick_queue)
    queued_data = await shared_queue.get()
    market_data = aggregator.create_market_data(queued_data)
    symbol = market_data.S

    handler = aggregator.stock_handlers[symbol]
    handler.process_trade(
        price=market_data.p,
        volume=market_data.s,
        timestamp=market_data.t,
        conditions=market_data.c
    )

    # Verify SSE broadcast was triggered
    assert len(sse_broadcasts) > 0
    last_broadcast = sse_broadcasts[-1]
    assert last_broadcast['symbol'] == 'AAPL'
    assert last_broadcast['is_initial'] is False  # Live update


@pytest.mark.asyncio
async def test_multiple_users_same_symbol():
    """Test multiple users subscribing to same symbol"""
    # Create components
    shared_queue = asyncio.Queue(500)
    aggregator = TradeDataAggregator(input_queue=shared_queue)

    subscription_manager = SubscriptionManager(
        subscribe_callback=AsyncMock(return_value=True),
        on_handler_create_callback=aggregator.ensure_handler_exists
    )

    # Multiple users subscribe to same symbol
    await subscription_manager.add_user_subscription(1, "AAPL")
    await subscription_manager.add_user_subscription(2, "AAPL")
    await subscription_manager.add_user_subscription(3, "AAPL")

    # Should only create ONE handler
    assert len(aggregator.stock_handlers) == 1
    assert 'AAPL' in aggregator.stock_handlers

    # All users should be tracked
    assert len(subscription_manager.user_subscriptions) == 3


@pytest.mark.asyncio
async def test_subscription_flow_historical_then_live():
    """Test complete flow: subscription → historical load → live data"""
    sse_broadcasts = []

    def mock_broadcast(update_data):
        sse_broadcasts.append(update_data)

    # Mock historical data
    mock_historical_fetcher = Mock()
    mock_historical_fetcher.fetch_historical_bars = AsyncMock(return_value=[
        BarData(
            T='b', S='TSLA', o=700.0, h=705.0, l=695.0, c=702.0,
            v=50000, t='2022-01-01T09:30:00Z', n=200, vw=701.0
        )
    ])

    # Create components
    shared_queue = asyncio.Queue(500)
    aggregator = TradeDataAggregator(
        input_queue=shared_queue,
        broadcast_callback=mock_broadcast,
        historical_fetcher=mock_historical_fetcher
    )

    subscription_manager = SubscriptionManager(
        subscribe_callback=AsyncMock(return_value=True),
        on_handler_create_callback=aggregator.ensure_handler_exists
    )

    # Subscribe
    await subscription_manager.add_user_subscription(1, "TSLA")

    # Wait for historical load
    await asyncio.sleep(0.3)

    # Should have broadcast historical data (is_initial=True)
    initial_broadcasts = [b for b in sse_broadcasts if b.get('is_initial')]
    assert len(initial_broadcasts) > 0

    # Now simulate live trade
    live_trade = TradeData(
        T='t', S='TSLA', i=999, x='V', p=705.0, s=200,
        c=[], t='2022-01-01T09:31:30Z', z='A'
    )

    await shared_queue.put(live_trade)
    queued_data = await shared_queue.get()
    market_data = aggregator.create_market_data(queued_data)

    handler = aggregator.stock_handlers['TSLA']
    handler.process_trade(
        price=market_data.p,
        volume=market_data.s,
        timestamp=market_data.t,
        conditions=market_data.c
    )

    # Should have broadcast live update (is_initial=False)
    live_broadcasts = [b for b in sse_broadcasts if not b.get('is_initial')]
    assert len(live_broadcasts) > 0

    # Verify both historical and live candles exist
    assert len(handler.candle_data) >= 2


@pytest.mark.asyncio
async def test_unsubscription_flow():
    """Test unsubscription removes user but keeps handler if others subscribed"""
    aggregator = TradeDataAggregator(input_queue=asyncio.Queue(500))

    subscription_manager = SubscriptionManager(
        subscribe_callback=AsyncMock(return_value=True),
        unsubscribe_callback=AsyncMock(return_value=True),
        on_handler_create_callback=aggregator.ensure_handler_exists
    )

    # Two users subscribe
    await subscription_manager.add_user_subscription(1, "NVDA")
    await subscription_manager.add_user_subscription(2, "NVDA")

    # Verify handler exists
    assert 'NVDA' in aggregator.stock_handlers

    # User 1 unsubscribes
    await subscription_manager.remove_user_subscription(1, "NVDA")

    # User 2 still subscribed
    assert 2 in subscription_manager.user_subscriptions
    assert 1 not in subscription_manager.user_subscriptions

    # Handler should still exist (user 2 still needs it)
    assert 'NVDA' in aggregator.stock_handlers


@pytest.mark.asyncio
async def test_concurrent_subscriptions_different_symbols():
    """Test concurrent subscriptions to different symbols"""
    aggregator = TradeDataAggregator(input_queue=asyncio.Queue(500))

    subscription_manager = SubscriptionManager(
        subscribe_callback=AsyncMock(return_value=True),
        on_handler_create_callback=aggregator.ensure_handler_exists
    )

    # Subscribe to multiple symbols concurrently
    await asyncio.gather(
        subscription_manager.add_user_subscription(1, "AAPL"),
        subscription_manager.add_user_subscription(1, "GOOGL"),
        subscription_manager.add_user_subscription(1, "MSFT"),
        subscription_manager.add_user_subscription(1, "AMZN"),
    )

    # All handlers should be created
    assert len(aggregator.stock_handlers) == 4
    assert all(symbol in aggregator.stock_handlers for symbol in ['AAPL', 'GOOGL', 'MSFT', 'AMZN'])


@pytest.mark.asyncio
async def test_handler_persistence_across_reconnects():
    """Test that handlers persist when websocket reconnects"""
    aggregator = TradeDataAggregator(input_queue=asyncio.Queue(500))

    # Simulate first connection
    subscription_manager_1 = SubscriptionManager(
        subscribe_callback=AsyncMock(return_value=True),
        on_handler_create_callback=aggregator.ensure_handler_exists
    )

    await subscription_manager_1.add_user_subscription(1, "AAPL")

    # Verify handler created
    assert 'AAPL' in aggregator.stock_handlers
    original_handler = aggregator.stock_handlers['AAPL']

    # Add some data to handler
    original_handler.process_trade(150.0, 100, "2022-01-01T09:30:00Z", [])

    # Simulate reconnection with new SubscriptionManager instance
    # (but same aggregator)
    subscription_manager_2 = SubscriptionManager(
        subscribe_callback=AsyncMock(return_value=True),
        on_handler_create_callback=aggregator.ensure_handler_exists
    )

    # Subscribe again after reconnect
    await subscription_manager_2.add_user_subscription(1, "AAPL")

    # Handler should be same instance (not recreated)
    assert aggregator.stock_handlers['AAPL'] is original_handler
    # Data should be preserved
    assert len(original_handler.candle_data) > 0


@pytest.mark.asyncio
async def test_error_handling_historical_fetch_fails():
    """Test that subscription succeeds even if historical fetch fails"""
    sse_broadcasts = []

    def mock_broadcast(update_data):
        sse_broadcasts.append(update_data)

    # Mock failing historical fetcher
    mock_historical_fetcher = Mock()
    mock_historical_fetcher.fetch_historical_bars = AsyncMock(side_effect=Exception("API Error"))

    aggregator = TradeDataAggregator(
        input_queue=asyncio.Queue(500),
        broadcast_callback=mock_broadcast,
        historical_fetcher=mock_historical_fetcher
    )

    subscription_manager = SubscriptionManager(
        subscribe_callback=AsyncMock(return_value=True),
        on_handler_create_callback=aggregator.ensure_handler_exists
    )

    # Subscribe should still succeed
    result = await subscription_manager.add_user_subscription(1, "AAPL")
    assert result is True

    # Handler should still be created
    assert 'AAPL' in aggregator.stock_handlers

    # Wait for background task to complete
    await asyncio.sleep(0.2)

    # Live data should still work
    handler = aggregator.stock_handlers['AAPL']
    handler.process_trade(150.0, 100, "2022-01-01T09:30:00Z", [])

    assert len(handler.candle_data) > 0


@pytest.mark.asyncio
async def test_sse_initial_vs_incremental_updates():
    """Test that SSE correctly differentiates between initial and incremental updates"""
    sse_broadcasts = []

    def mock_broadcast(update_data):
        sse_broadcasts.append(update_data)

    mock_historical_fetcher = Mock()
    mock_historical_fetcher.fetch_historical_bars = AsyncMock(return_value=[
        BarData(
            T='b', S='META', o=300.0, h=305.0, l=295.0, c=302.0,
            v=100000, t='2022-01-01T09:30:00Z', n=500, vw=301.0
        )
    ])

    aggregator = TradeDataAggregator(
        input_queue=asyncio.Queue(500),
        broadcast_callback=mock_broadcast,
        historical_fetcher=mock_historical_fetcher
    )

    subscription_manager = SubscriptionManager(
        subscribe_callback=AsyncMock(return_value=True),
        on_handler_create_callback=aggregator.ensure_handler_exists
    )

    # Subscribe
    await subscription_manager.add_user_subscription(1, "META")

    # Wait for historical load
    await asyncio.sleep(0.3)

    # Find initial broadcast
    initial = [b for b in sse_broadcasts if b.get('is_initial') is True]
    assert len(initial) > 0

    # Process live trade
    handler = aggregator.stock_handlers['META']
    handler.process_trade(305.0, 200, "2022-01-01T09:31:30Z", [])

    # Find incremental broadcast
    incremental = [b for b in sse_broadcasts if b.get('is_initial') is False]
    assert len(incremental) > 0

    # Initial should have more candles than incremental
    initial_candles = initial[0]['candles']
    incremental_candles = incremental[0]['candles']

    # Incremental should only have last 2 candles
    assert len(incremental_candles) <= 2
