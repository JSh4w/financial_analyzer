"""Main backend application using FastAPI for stock analysis"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from logging import getLogger
from typing import Dict, TypedDict

import httpx

# Authentication
from app.auth import warmup_jwks
from app.config import Settings  # Configuration settings

# Single writer for DuckDB to avoid concurrency issues
from app.database.connection import DuckDBConnection
from app.database.external_database_manager import DatabaseManager
from app.database.news_data_manager import (
    NewsDataManager,  # Handles user subsriptions and SSE
)
from app.database.stock_data_manager import StockDataManager
from app.database.subscription_manager import PersistentSubscriptionManager

# News manager functions
from app.managers.news_manager import broadcast_news

# SSE manager functions
from app.managers.sse_manager import broadcast_update
from app.routes.aggregator import router as aggregator_router
from app.routes.banking import banking_router
from app.routes.database import router as database_router
from app.routes.investments import investments_router
from app.routes.persistent_subcriptions import router as persistent_subscriptions_router
from app.routes.snaptrade import broker_route
from app.routes.stream import router as stream_router

# API routes
from app.routes.t212 import t212_router
from app.routes.tradingview import router as tradingview_router
from app.routes.websocket_subcriptions import router as websocket_subscriptions_router

# banking class
from app.services.gocardless import GoCardlessClient
from app.stocks.data_aggregator import TradeDataAggregator  # Creates candlesticks
from app.stocks.historical_data import AlpacaHistoricalData  # Requests historical data
from app.stocks.news_websocket import NewsWebsocket  # Initial news websocket
from app.stocks.subscription_manager import SubscriptionManager
from app.stocks.websocket_manager import WebSocketManager  # Sets up initial connection
from app.utils import connect_and_start_websocket  # Util function for class
from core.logging import setup_logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    ws_manager = await connect_and_start_websocket(
        websocket=WebSocketManager,
        uri="wss://stream.data.alpaca.markets/v2/iex",
        output_queue=shared_queue,
    )
    demo_ws_manager = await connect_and_start_websocket(
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
    news_ws = await connect_and_start_websocket(
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
    active_subscriptions = (
        persistent_subscription_manager.get_all_active_subscriptions()
    )

    if active_subscriptions:
        logger.info(
            f"Rehydrating {len(active_subscriptions)} user-symbol subscriptions from database"
        )
        for user_id, symbol in active_subscriptions:
            try:
                manager = (
                    demo_subscription_manager
                    if symbol == "FAKEPACA"
                    else subscription_manager
                )

                await manager.add_user_subscription(
                    user_id=user_id,
                    symbol=symbol,
                    subscription_type="trades",
                )
                logger.info(f"✓ Rehydrated {symbol} for user {user_id}")
            except Exception as e:
                logger.error(f"✗ Failed to rehydrate {symbol} for user {user_id}: {e}")
    else:
        logger.info("No active subscriptions to rehydrate")

    # Pre-fetch JWKS keys so auth works immediately on first request
    await warmup_jwks()

    # brokerage singleton
    brokerage_client = SnapTrade(
        consumer_key=settings.SNAPTRADE_CONSUMER_KEY,
        client_id=settings.SNAPTRADE_CLIENT_ID,
    )

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
        "brokerage_client": brokerage_client,
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
app.include_router(broker_route)
app.include_router(investments_router)
app.include_router(persistent_subscriptions_router)
app.include_router(websocket_subscriptions_router)
app.include_router(aggregator_router)
app.include_router(stream_router)
app.include_router(database_router)
app.include_router(tradingview_router)


@app.get("/health")
def health_check():
    """Check if application is running"""
    return {
        "status": "healthy",
        "service": "stock-service",
        "environment": "production",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        timeout_graceful_shutdown=5,  # Force close connections after 5 seconds
    )
