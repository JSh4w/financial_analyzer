"""Main backend application using FastAPI for stock analysis"""

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from logging import getLogger
from typing import Dict, List, TypedDict

import httpx

# AUthentication
from app.auth import get_current_user_id
from app.config import Settings  # Configuration settings
from app.database.connection import DuckDBConnection
from app.database.external_database_manager import DatabaseManager
from app.database.news_data_manager import (
    NewsDataManager,  # Handles user subsriptions and SSE
)
from app.database.stock_data_manager import (
    StockDataManager,  # For DB access of candles / long term
)
from app.database.subscription_manager import PersistentSubscriptionManager

# Dependency functions
from app.dependencies import (
    get_data_aggregator,
    get_db_manager,
    get_demo_subscription_manager,
    get_persistent_subscription_manager,
    get_subscription_manager,
    get_ws_manager,
)
from app.routes.banking import banking_router

# API routes
from app.routes.t212 import t212_router

# banking class
from app.services.gocardless import GoCardlessClient
from app.stocks.data_aggregator import TradeDataAggregator  # Creates candlesticks
from app.stocks.historical_data import AlpacaHistoricalData  # Requests historical data
from app.stocks.news_websocket import NewsWebsocket  # Initial news websocket
from app.stocks.subscription_manager import (
    SubscriptionManager,  # For users to interact with websocket
)
from app.stocks.websocket_manager import WebSocketManager  # Sets up initial connection
from app.utils import time_function  # Timing a function request
from core.logging import setup_logging
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# brokerage imports
from snaptrade_client import SnapTrade

setup_logging(level="DEBUG")
logger = getLogger(__name__)

settings = Settings()


# Define typed application state
class State(TypedDict):
    """Application state with type definitions"""

    db_manager: StockDataManager
    data_aggregator: TradeDataAggregator
    ws_manager: WebSocketManager
    demo_ws_manager: WebSocketManager
    subscription_manager: SubscriptionManager
    demo_subscription_manager: SubscriptionManager
    news_queue: asyncio.Queue
    news_db_manager: NewsDataManager
    news_ws: NewsWebsocket
    news_broadcast_task: asyncio.Task
    banking_client: GoCardlessClient
    supabase_db: DatabaseManager
    persistent_subscription_manager: PersistentSubscriptionManager


# SSE connection management
# Structure: {symbol: {user_id: asyncio.Queue}}
active_sse_connections: Dict[str, Dict[str, asyncio.Queue]] = {}

# Since each person consumes a queue, we need one per news connection
active_news_connections: List[asyncio.Queue] = []

# TODO: Add news cache for historical data on connect
# from collections import deque
# news_cache = deque(maxlen=100)  # Keep last 100 news items for new connections


### --- News broadcast handling ---
async def broadcast_news(news_queue: asyncio.Queue):
    """Broadcast news data to the frontend"""
    while True:
        item = await news_queue.get()
        if item is None:
            break  # sentinal

        # TODO: Add to cache for new connections
        # news_cache.append(item)

        # Remove dead queues during broadcast
        dead_queues = []
        for queue in active_news_connections:
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                logger.warning("News queue full for a connection, dropping")
            except Exception as e:
                logger.error("Error broadcasting to queue: %s", e)
                dead_queues.append(queue)

        for queue in dead_queues:
            try:
                active_news_connections.remove(queue)
            except ValueError:
                pass


def add_news_connection(queue: asyncio.Queue):
    """Add user for news information"""
    active_news_connections.append(queue)


def remove_news_connection(queue: asyncio.Queue):
    """Remove user for news information"""
    active_news_connections.remove(queue)


### --- Server Side Event Connection Handling ---
@time_function("broadcast_update")
def broadcast_update(update_data: dict):
    """Broadcast update to all SSE connections for a symbol"""
    symbol = update_data.get("symbol")
    is_initial = update_data.get("is_initial", False)

    if symbol and symbol in active_sse_connections:
        user_connections = active_sse_connections[symbol]
        connection_count = len(user_connections)

        # Remove any dead connections while broadcasting
        dead_users = []
        successful_broadcasts = 0

        for user_id, queue in user_connections.items():
            try:
                # For delta updates, only send to already-initialized connections
                # For initial updates, send to all connections
                if is_initial or hasattr(queue, "_initialized"):
                    queue.put_nowait(update_data)
                    successful_broadcasts += 1
                    # Mark queue as initialized after first message
                    if is_initial:
                        queue._initialized = True
            except asyncio.QueueFull:
                # Mark for removal if queue is full
                dead_users.append(user_id)
                logger.warning(
                    "SSE queue full for %s user %s, removing connection",
                    symbol,
                    user_id,
                )
            except Exception as e:
                # Mark for removal if any other error
                dead_users.append(user_id)
                logger.warning(
                    "SSE broadcast error for %s user %s: %s", symbol, user_id, e
                )

        # Clean up dead connections
        for dead_user in dead_users:
            try:
                del active_sse_connections[symbol][dead_user]
            except KeyError:
                pass

        logger.debug(
            "Broadcasted to %s/%s SSE connections for %s",
            successful_broadcasts,
            connection_count,
            symbol,
        )
    else:
        logger.debug("No SSE connections for symbol %s", symbol)


async def add_sse_connection(
    symbol: str, user_id: str, queue: asyncio.Queue
) -> asyncio.Queue | None:
    """
    Add an SSE connection queue for a symbol and user.
    Returns the old queue if user already had a connection (for cleanup).
    """
    if symbol not in active_sse_connections:
        active_sse_connections[symbol] = {}

    old_queue = active_sse_connections[symbol].get(user_id)
    active_sse_connections[symbol][user_id] = queue

    if old_queue:
        logger.info(
            "Replacing existing SSE connection for user %s on symbol %s",
            user_id,
            symbol,
        )

    return old_queue


async def remove_sse_connection(
    symbol: str,
    user_id: str,
    persistent_manager: PersistentSubscriptionManager = None,
    subscription_manager: SubscriptionManager = None,
    demo_subscription_manager: SubscriptionManager = None,
):
    """
    Remove an SSE connection for a symbol and user.
    If no SSE connections AND no permanent subscribers remain, unsubscribe from Alpaca.
    """
    if symbol in active_sse_connections:
        try:
            # Remove this user's connection
            if user_id in active_sse_connections[symbol]:
                del active_sse_connections[symbol][user_id]

            sse_connections_remaining = len(active_sse_connections.get(symbol, {}))

            if not active_sse_connections[symbol]:
                del active_sse_connections[symbol]
                sse_connections_remaining = 0

            # Check if we should unsubscribe from Alpaca WebSocket
            if persistent_manager and subscription_manager:
                permanent_subscribers = persistent_manager.get_symbol_subscriber_count(
                    symbol
                )

                logger.debug(
                    f"SSE closed for {symbol} (user {user_id}): {sse_connections_remaining} SSE remaining, "
                    f"{permanent_subscribers} permanent subscribers"
                )

                # Only unsubscribe if NO SSE connections AND NO permanent subscribers
                if sse_connections_remaining == 0 and permanent_subscribers == 0:
                    manager = (
                        demo_subscription_manager
                        if symbol == "FAKEPACA"
                        else subscription_manager
                    )
                    if manager:
                        try:
                            await manager.remove_user_subscription(
                                user_id="system",
                                symbol=symbol,
                                subscription_type="trades",
                            )
                            logger.info(
                                f"Unsubscribed from {symbol} on Alpaca (no active users)"
                            )
                        except Exception as e:
                            logger.error(f"Failed to unsubscribe from {symbol}: {e}")

        except KeyError:
            pass  # User not in connections


### --- websocket handling ---
async def connect_to_websocket(
    websocket=WebSocketManager, uri=None, output_queue=None, **kwargs
):
    """Connect to the WebSocketManager and return it started"""
    ws_manager = websocket(uri=uri, output_queue=output_queue, **kwargs)
    try:
        await ws_manager.start()
        print("websocket manager started")
        return ws_manager
    except Exception as e:
        print(f"Error starting websocket manager: {e}")
        await ws_manager.stop()
        raise e


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[Dict]:
    """FastAPI lifespan manager - startup and shutdown events"""
    # STARTUP: Initialize components when app starts
    logger.info("Starting application components...")

    # Initialize database manager
    db_connection = DuckDBConnection("data/stock_data.duckdb")
    db_manager = StockDataManager(db_connection=db_connection)

    # Websocket queue, max number of stocks
    shared_queue = asyncio.Queue(500)

    # Initialize historical data fetcher
    historical_fetcher = AlpacaHistoricalData(
        api_key=settings.ALPACA_API_KEY, api_secret=settings.ALPACA_API_SECRET
    )

    # Initialize data aggregator with all components
    data_aggregator = TradeDataAggregator(
        input_queue=shared_queue,
        broadcast_callback=broadcast_update,
        db_manager=db_manager,
        historical_fetcher=historical_fetcher,
    )

    # Start processing task
    aggregator_task = asyncio.create_task(data_aggregator.process_tick_queue())

    # Initialize WebSocket manager with the shared queue
    # "wss://stream.data.alpaca.markets/v2/test for FAKEPACA
    # "wss://stream.data.alpaca.markets/v2/iex"
    ws_manager = await connect_to_websocket(
        websocket=WebSocketManager,
        uri="wss://stream.data.alpaca.markets/v2/iex",
        output_queue=shared_queue,
    )
    demo_ws_manager = await connect_to_websocket(
        websocket=WebSocketManager,
        uri="wss://stream.data.alpaca.markets/v2/test",
        output_queue=shared_queue,
    )

    # Initialize SubscriptionManager (source of truth for subscriptions)
    subscription_manager = SubscriptionManager(
        subscribe_callback=ws_manager.subscribe,
        unsubscribe_callback=ws_manager.unsubscribe,
        on_handler_create_callback=data_aggregator.ensure_handler_exists,
    )

    demo_subscription_manager = SubscriptionManager(
        subscribe_callback=demo_ws_manager.subscribe,
        unsubscribe_callback=demo_ws_manager.unsubscribe,
        on_handler_create_callback=data_aggregator.ensure_handler_exists,
    )

    logger.info("SubscriptionManager initialized and wired")

    # Handle news
    news_queue = asyncio.Queue(500)
    news_db_manager = NewsDataManager(db_connection=db_connection)
    news_ws = await connect_to_websocket(
        websocket=NewsWebsocket,
        uri="wss://stream.data.alpaca.markets/v1beta1/news",
        output_queue=news_queue,
    )

    news_broadcast_task = asyncio.create_task(broadcast_news(news_queue))

    # Initialize GoCardless client for banking operations
    banking_http_client = httpx.AsyncClient(
        base_url="https://bankaccountdata.gocardless.com",
        headers={"accept": "application/json"},
        timeout=10.0,
    )
    banking_client = GoCardlessClient(
        secret_id=settings.GO_CARDLESS_SECRET_ID,
        secret_key=settings.GO_CARDLESS_SECRET_KEY,
        http_client=banking_http_client,
    )

    # Initialize Supabase database manager for user data and banking requisitions
    supabase_db = DatabaseManager()
    supabase_db.connect()
    logger.info("Supabase DatabaseManager initialized")

    # Initialize persistent subscription manager
    persistent_subscription_manager = PersistentSubscriptionManager(supabase_db)
    logger.info("Persistent SubscriptionManager initialized")

    # Rehydrate subscriptions from database
    active_symbols = persistent_subscription_manager.get_active_symbols(use_cache=False)

    if active_symbols:
        logger.info(
            f"Rehydrating {len(active_symbols)} subscriptions from database: {active_symbols}"
        )
        for symbol in active_symbols:
            try:
                # Determine which manager to use (demo or production)
                manager = (
                    demo_subscription_manager
                    if symbol == "FAKEPACA"
                    else subscription_manager
                )

                # Subscribe to WebSocket (uses dummy user_id since this is system-level)
                await manager.add_user_subscription(
                    user_id="system",  # System-initiated subscription
                    symbol=symbol,
                    subscription_type="trades",
                )
                logger.info(f"✓ Rehydrated subscription for {symbol}")
            except Exception as e:
                logger.error(f"✗ Failed to rehydrate {symbol}: {e}")
    else:
        logger.info("No active subscriptions to rehydrate")

    # brokerage singleton
    snaptrade_client = SnapTrade()

    # Yield state to FastAPI - this makes it available via request.state
    yield {
        "db_manager": db_manager,
        "data_aggregator": data_aggregator,
        "ws_manager": ws_manager,
        "demo_ws_manager": demo_ws_manager,
        "subscription_manager": subscription_manager,
        "demo_subscription_manager": demo_subscription_manager,
        "news_queue": news_queue,
        "news_db_manager": news_db_manager,
        "news_ws": news_ws,
        "news_broadcast_task": news_broadcast_task,
        "banking_client": banking_client,
        "supabase_db": supabase_db,
        "persistent_subscription_manager": persistent_subscription_manager,
    }

    # SHUTDOWN: Clean up when app stops
    logger.info("Shutting down application components...")

    aggregator_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await aggregator_task

    await data_aggregator.shutdown()
    await ws_manager.stop()
    await demo_ws_manager.stop()
    await news_ws.stop()

    # Stop news broadcast task
    await news_queue.put(None)  # Sentinel to stop broadcast loop
    news_broadcast_task.cancel()
    try:
        await news_broadcast_task
    except asyncio.CancelledError:
        pass
    logger.info("News broadcast task stopped")

    db_manager.close()


app = FastAPI(
    title="Stock Market Data Service",
    description="Real-time stock market data and websocket service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(t212_router)
app.include_router(banking_router)


@app.get("/health")
def health_check():
    """Check if application is running"""
    return {
        "status": "healthy",
        "service": "stock-service",
        "environment": "production",
    }


@app.get("/ws_manager/status")
async def status(
    ws_manager: WebSocketManager = Depends(get_ws_manager),
    _: str = Depends(get_current_user_id),
):
    """Check status of ws_manager"""
    output = await ws_manager.log_current_status()
    return {"message": f"{output}"}


@app.get("/ws_manager/{symbol}")
async def subscribe_to_symbol(
    symbol: str,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(
        get_demo_subscription_manager
    ),
    user_id: str = Depends(get_current_user_id),
):
    """Subscribe to symbol stock data via SubscriptionManager"""
    # Use demo manager for FAKEPACA, otherwise use production manager
    manager = (
        demo_subscription_manager if symbol == "FAKEPACA" else subscription_manager
    )

    if manager is None:
        return {"message": "Subscription manager is not running", "status": "error"}

    try:
        # SubscriptionManager orchestrates: StockHandler creation + WebSocket subscription
        success = await manager.add_user_subscription(
            user_id=user_id, symbol=symbol, subscription_type="trades"
        )

        if success:
            return {
                "message": "Subscribed to symbol successfully",
                "status": "subscribed",
                "symbol": symbol,
            }

        return {"message": f"Failed to subscribe to {symbol}", "status": "error"}
    except Exception as e:
        logger.error("Subscription error for %s: %s", symbol, e)
        return {
            "message": f"Failed to subscribe to {symbol}: {str(e)}",
            "status": "error",
        }


@app.get("/ws_manager/close/{symbol}")
async def unsubscribe_to_symbol(
    symbol: str,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(
        get_demo_subscription_manager
    ),
    user_id: str = Depends(get_current_user_id),
):
    """Unsubscribe from symbol stock data via SubscriptionManager"""
    # Use demo manager for FAKEPACA, otherwise use production manager
    manager = (
        demo_subscription_manager if symbol == "FAKEPACA" else subscription_manager
    )

    if manager is None:
        return {
            "message": "Subscription manager is not running",
            "status": "not_running",
        }

    try:
        success = await manager.remove_user_subscription(
            user_id=user_id, symbol=symbol, subscription_type="trades"
        )

        if success:
            return {
                "message": "Unsubscribed from symbol successfully",
                "status": "unsubscribed",
                "symbol": symbol,
            }
        else:
            return {
                "message": f"Failed to unsubscribe from {symbol}",
                "status": "error",
            }
    except Exception as e:
        logger.error("Unsubscription error for %s: %s", symbol, e)
        return {
            "message": f"Failed to unsubscribe from {symbol}: {str(e)}",
            "status": "error",
        }


# Persistent Subscription Endpoints (New)
@app.post("/api/subscribe/{symbol}")
async def create_persistent_subscription(
    symbol: str,
    user_id: str = Depends(get_current_user_id),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(
        get_demo_subscription_manager
    ),
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    persistent_manager: PersistentSubscriptionManager = Depends(
        get_persistent_subscription_manager
    ),
):
    """
    Subscribe user to a symbol with persistent storage in database
    This combines database persistence with WebSocket subscription
    """
    symbol = symbol.upper()

    try:
        # Save to database (persistent)
        success = persistent_manager.subscribe_user(user_id, symbol)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to create persistent subscription"
            )

        # Check if we need to subscribe to Alpaca WebSocket
        if symbol not in data_aggregator.get_all_symbols():
            # First subscriber - create WebSocket subscription
            manager = (
                demo_subscription_manager
                if symbol == "FAKEPACA"
                else subscription_manager
            )

            if manager is None:
                raise HTTPException(
                    status_code=503, detail="Subscription manager not running"
                )

            ws_success = await manager.add_user_subscription(
                user_id=user_id, symbol=symbol, subscription_type="trades"
            )

            if not ws_success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to subscribe to market data for {symbol}",
                )

            logger.info(f"Subscribed to {symbol} on Alpaca for user {user_id}")

        subscriber_count = persistent_manager.get_symbol_subscriber_count(symbol)

        return {
            "status": "subscribed",
            "symbol": symbol,
            "subscriber_count": subscriber_count,
            "message": f"Successfully subscribed to {symbol}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create subscription for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/subscribe/{symbol}")
async def delete_persistent_subscription(
    symbol: str,
    user_id: str = Depends(get_current_user_id),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(
        get_demo_subscription_manager
    ),
    persistent_manager: PersistentSubscriptionManager = Depends(
        get_persistent_subscription_manager
    ),
):
    """
    Unsubscribe user from a symbol (marks as inactive in database)
    Only unsubscribes from Alpaca if no other users are watching the symbol
    """
    symbol = symbol.upper()

    try:
        # Mark as inactive in database
        persistent_manager.unsubscribe_user(user_id, symbol)

        # Check if we should unsubscribe from Alpaca
        if persistent_manager.should_unsubscribe_from_alpaca(symbol):
            manager = (
                demo_subscription_manager
                if symbol == "FAKEPACA"
                else subscription_manager
            )

            if manager:
                await manager.remove_user_subscription(
                    user_id=user_id, symbol=symbol, subscription_type="trades"
                )
                logger.info(f"Unsubscribed from {symbol} on Alpaca (no active users)")

        remaining = persistent_manager.get_symbol_subscriber_count(symbol)

        return {
            "status": "unsubscribed",
            "symbol": symbol,
            "remaining_subscribers": remaining,
            "message": f"Successfully unsubscribed from {symbol}",
        }

    except Exception as e:
        logger.error(f"Failed to unsubscribe from {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/subscriptions")
async def get_user_persistent_subscriptions(
    user_id: str = Depends(get_current_user_id),
    persistent_manager: PersistentSubscriptionManager = Depends(
        get_persistent_subscription_manager
    ),
):
    """
    Get all active subscriptions for the current user (their watchlist)
    """
    try:
        symbols = persistent_manager.get_user_subscriptions(user_id)

        return {"symbols": symbols, "count": len(symbols)}

    except Exception as e:
        logger.error(f"Failed to get subscriptions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/snapshot/{symbol}")
async def get_symbol_snapshot(
    symbol: str,
    _: str = Depends(get_current_user_id),
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
):
    """
    Get current snapshot of all candles for a symbol
    Used by SSE service to send initial data to clients
    """
    symbol = symbol.upper()

    if data_aggregator is None:
        raise HTTPException(status_code=503, detail="Data aggregator not running")

    handler = data_aggregator.get_stock_handler(symbol)
    if not handler:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not subscribed")

    return {
        "symbol": symbol,
        "candles": handler.candle_data,
        "update_timestamp": datetime.now(timezone.utc).isoformat(),
        "is_initial": True,
    }


# Data Aggregator Endpoints
@app.get("/aggregator/status")
async def get_aggregator_status(
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    _: str = Depends(get_current_user_id),
):
    """Get status of the data aggregator"""
    if data_aggregator is None:
        return {"status": "stopped", "message": "Data aggregator is not running"}

    return {
        "status": "running",
        "symbols_tracked": data_aggregator.get_all_symbols(),
        "queue_size": data_aggregator.queue.qsize(),
    }


@app.get("/aggregator/symbols")
async def get_tracked_symbols(
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    _: str = Depends(get_current_user_id),
):
    """Get all symbols being tracked by the aggregator"""
    if data_aggregator is None:
        return {"error": "Data aggregator is not running"}

    return {"symbols": data_aggregator.get_all_symbols()}


@app.get("/aggregator/data/{symbol}")
async def get_symbol_data(
    symbol: str,
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    _: str = Depends(get_current_user_id),
):
    """Get OHLCV data for a specific symbol"""
    if data_aggregator is None:
        return {"error": "Data aggregator is not running"}

    stock_handler = data_aggregator.get_stock_handler(symbol.upper())
    if stock_handler is None:
        return {"error": f"No data found for symbol {symbol}"}

    return {"symbol": symbol.upper(), "candle_data": stock_handler.candle_data}


@app.get("/aggregator/data")
async def get_all_aggregated_data(
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    _: str = Depends(get_current_user_id),
):
    """Get OHLCV data for all tracked symbols"""
    if data_aggregator is None:
        return {"error": "Data aggregator is not running"}

    all_data = {}
    for symbol in data_aggregator.get_all_symbols():
        stock_handler = data_aggregator.get_stock_handler(symbol)
        if stock_handler:
            all_data[symbol] = stock_handler.candle_data

    return {"data": all_data}


# SSE Streaming Endpoints
@app.get("/stream/{symbol}")
async def stream_stock_data(
    symbol: str,
    token: str,
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    persistent_manager: PersistentSubscriptionManager = Depends(
        get_persistent_subscription_manager
    ),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(
        get_demo_subscription_manager
    ),
):
    """Stream real-time OHLCV data for a symbol via SSE"""
    # Validate token from query parameter (EventSource doesn't support headers)
    from app.auth import decode_jwt_token

    user = decode_jwt_token(token)
    user_id = user.sub

    symbol = symbol.upper()

    # Check if data aggregator is running
    if data_aggregator is None:
        raise HTTPException(status_code=503, detail="Data aggregator not running")

    # Check if symbol is already being tracked (has active WebSocket subscription)
    if symbol not in data_aggregator.get_all_symbols():
        raise HTTPException(
            status_code=400,
            detail=f"Symbol {symbol} not subscribed. Please subscribe via WebSocket first.",
        )

    # Create SSE queue for this connection
    sse_queue = asyncio.Queue(maxsize=10)

    # Add connection (this replaces any existing connection for this user/symbol)
    old_queue = await add_sse_connection(symbol, user_id, sse_queue)

    # If user had an existing connection, close it gracefully
    if old_queue:
        try:
            # Send a termination signal to the old queue
            old_queue.put_nowait({"_terminate": True})
        except asyncio.QueueFull:
            pass  # Old queue is full, it will be cleaned up anyway

    # Send initial data immediately (full snapshot)
    stock_handler = data_aggregator.get_stock_handler(symbol)
    if stock_handler and stock_handler.candle_data:
        initial_data = {
            "symbol": symbol,
            "candles": stock_handler.candle_data,
            "update_timestamp": datetime.now(timezone.utc).isoformat(),
            "is_initial": True,
        }
        await sse_queue.put(initial_data)
        # Mark this queue as initialized
        sse_queue._initialized = True

    async def event_stream():
        try:
            while True:
                update_data = await sse_queue.get()

                # Check for termination signal (old connection being replaced)
                if isinstance(update_data, dict) and update_data.get("_terminate"):
                    logger.info(
                        "SSE connection replaced for user %s on %s", user_id, symbol
                    )
                    break

                yield f"data: {json.dumps(update_data)}\n\n"
        except asyncio.CancelledError:
            logger.info("Stock stream cancelled for user %s on %s", user_id, symbol)
        except Exception as e:
            logger.error("Stock stream error for user %s on %s: %s", user_id, symbol, e)
        finally:
            # Pass managers to check if we should unsubscribe from Alpaca
            await remove_sse_connection(
                symbol,
                user_id,
                persistent_manager=persistent_manager,
                subscription_manager=subscription_manager,
                demo_subscription_manager=demo_subscription_manager,
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# Database Management Endpoints
@app.get("/database/stats")
async def get_database_stats(
    db_manager: StockDataManager = Depends(get_db_manager),
    _: str = Depends(get_current_user_id),
):
    """Get database statistics for all symbols"""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database manager not running")

    try:
        stats = db_manager.get_symbols_stats()
        return {
            "stats": [
                {
                    "symbol": row[0],
                    "candle_count": row[1],
                    "first_candle": row[2],
                    "last_candle": row[3],
                    "last_updated": str(row[4]),
                }
                for row in stats
            ],
            "total_symbols": len(stats),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e


@app.get("/database/export/{symbol}")
async def export_symbol_data(
    symbol: str,
    db_manager: StockDataManager = Depends(get_db_manager),
    _: str = Depends(get_current_user_id),
):
    """Export symbol data to parquet file"""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database manager not running")

    try:
        output_file = db_manager.export_to_parquet(symbol.upper())
        if output_file:
            return {"message": "Data exported successfully", "file": output_file}
        else:
            raise HTTPException(status_code=500, detail="Export failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}") from e


@app.get("/database/candle_count/{symbol}")
async def get_candle_count(
    symbol: str,
    db_manager: StockDataManager = Depends(get_db_manager),
    _: str = Depends(get_current_user_id),
):
    """Get candle count for a specific symbol"""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database manager not running")

    try:
        count = db_manager.get_candle_count(symbol.upper())
        return {"symbol": symbol.upper(), "candle_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e


# TradingView Datafeed API Endpoints
@app.get("/api/tradingview/config")
async def tradingview_config():
    """TradingView UDF configuration endpoint"""
    return {
        "supports_search": False,
        "supports_group_request": False,
        "supports_marks": False,
        "supports_timescale_marks": False,
        "supports_time": True,
        "supported_resolutions": ["1"],  # Only 1-minute bars for now
    }


@app.get("/api/tradingview/symbol_info")
async def tradingview_symbol_info(symbol: str):
    """Resolve symbol information for TradingView"""
    return {
        "name": symbol.upper(),
        "ticker": symbol.upper(),
        "description": f"{symbol.upper()} Stock",
        "type": "stock",
        "session": "0930-1600",
        "exchange": "US",
        "listed_exchange": "US",
        "timezone": "America/New_York",
        "minmov": 1,
        "pricescale": 100,
        "has_intraday": True,
        "supported_resolutions": ["1"],
        "volume_precision": 0,
        "data_status": "streaming",
    }


@app.get("/api/tradingview/history")
async def tradingview_history(
    symbol: str,
    from_ts: int,
    to_ts: int,
    resolution: str = "1",  # noqa: ARG001 - Reserved for future multi-resolution support
    db_manager: StockDataManager = Depends(get_db_manager),
    _: str = Depends(get_current_user_id),
):
    """Get historical bars for TradingView

    Args:
        symbol: Stock symbol
        from_ts: Unix timestamp (seconds) - start time
        to_ts: Unix timestamp (seconds) - end time
        resolution: Bar resolution (only "1" minute supported now)

    Returns:
        TradingView UDF format:
        {s: "ok", t: [...], o: [...], h: [...], l: [...], c: [...], v: [...]}
    """
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Convert Unix timestamps to RFC-3339 format
        from_dt = datetime.fromtimestamp(from_ts, tz=timezone.utc)
        to_dt = datetime.fromtimestamp(to_ts, tz=timezone.utc)

        from_timestamp = from_dt.isoformat().replace("+00:00", "Z")
        to_timestamp = to_dt.isoformat().replace("+00:00", "Z")

        # Query database
        candles = db_manager.get_candles_by_time_range(
            symbol.upper(), from_timestamp, to_timestamp
        )

        if not candles:
            return {"s": "no_data", "nextTime": None}

        # Transform to TradingView format
        tv_bars = {
            "s": "ok",
            "t": [],  # timestamps (unix seconds)
            "o": [],  # open
            "h": [],  # high
            "l": [],  # low
            "c": [],  # close
            "v": [],  # volume
        }

        for timestamp, candle in sorted(candles.items()):
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            tv_bars["t"].append(int(dt.timestamp()))
            tv_bars["o"].append(candle["open"])
            tv_bars["h"].append(candle["high"])
            tv_bars["l"].append(candle["low"])
            tv_bars["c"].append(candle["close"])
            tv_bars["v"].append(candle["volume"])

        logger.info(
            "Returned %s bars for %s from %s to %s",
            len(tv_bars["t"]),
            symbol,
            from_timestamp,
            to_timestamp,
        )
        return tv_bars

    except Exception as e:
        logger.error("TradingView history error for %s: %s", symbol, e)
        raise HTTPException(
            status_code=500, detail=f"Error fetching history: {str(e)}"
        ) from e


@app.get("/news/stream")
async def stream_news_data(token: str):
    """Stream news data via SSE"""
    # Validate token from query parameter (EventSource doesn't support headers)
    try:
        from app.auth import decode_jwt_token

        user = decode_jwt_token(token)
        user_id = user.sub
    except HTTPException as e:
        logger.warning("News stream auth failed: %s", e.detail)
        raise HTTPException(
            status_code=401, detail="Invalid token for news stream"
        ) from e

    n_queue = asyncio.Queue(maxsize=10)
    add_news_connection(n_queue)

    async def event_stream():
        try:
            while True:
                update_data = await n_queue.get()

                # Handle shutdown signal
                if update_data is None:
                    logger.info("News stream shutdown signal received")
                    break
                try:
                    update_data = NewsWebsocket.process_news_data(update_data)
                    yield f"data: {json.dumps(update_data)}\n\n"
                except (KeyError, ValueError) as e:
                    logger.warning("Invalid news data, skipping: %s", e)
                    continue
        except asyncio.CancelledError:
            logger.info("News stream cancelled by client disconnect")
        except Exception as e:
            logger.error("Unexpected error in news stream: %s", e)
        finally:
            remove_news_connection(queue=n_queue)
            logger.debug("News connection cleaned up")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        timeout_graceful_shutdown=5,  # Force close connections after 5 seconds
    )
