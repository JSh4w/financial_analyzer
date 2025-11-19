"""Main backend application using FastAPI for stock analysis"""
import json
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from logging import getLogger
from typing import Dict, List
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import Settings
from app.utils import time_function
from app.stocks.websocket_manager import WebSocketManager
from app.stocks.data_aggregator import TradeDataAggregator
from app.stocks.historical_data import AlpacaHistoricalData
from app.stocks.subscription_manager import SubscriptionManager
from app.database.stock_data_manager import StockDataManager

from app.stocks.news_websocket import NewsWebsocket
from app.database.news_data_manager import NewsDataManager

from app.database.connection import DuckDBConnection
from core.logging import setup_logging


setup_logging(level="DEBUG")
logger = getLogger(__name__)
load_dotenv()

settings = Settings()

# SSE connection management
active_sse_connections: Dict[str, List[asyncio.Queue]] = {}

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
            break #sentinal 

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
                logger.error("Error broadcasting to queue: %s",e)
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
        connection_count = len(active_sse_connections[symbol])

        # Remove any dead connections while broadcasting
        dead_queues = []
        successful_broadcasts = 0

        for queue in active_sse_connections[symbol]:
            try:
                # For delta updates, only send to already-initialized connections
                # For initial updates, send to all connections
                if is_initial or hasattr(queue, '_initialized'):
                    queue.put_nowait(update_data)
                    successful_broadcasts += 1
                    # Mark queue as initialized after first message
                    if is_initial:
                        queue._initialized = True
            except asyncio.QueueFull:
                # Mark for removal if queue is full
                dead_queues.append(queue)
                logger.warning("SSE queue full for %s, removing connection", symbol)
            except Exception as e:
                # Mark for removal if any other error
                dead_queues.append(queue)
                logger.warning("SSE broadcast error for %s: %s", symbol, e)

        # Clean up dead connections
        for dead_queue in dead_queues:
            try:
                active_sse_connections[symbol].remove(dead_queue)
            except ValueError:
                pass

        logger.debug("Broadcasted to %s/%s SSE connections for %s", successful_broadcasts, connection_count, symbol)
    else:
        logger.debug("No SSE connections for symbol %s", symbol)

async def add_sse_connection(symbol: str, queue: asyncio.Queue):
    """Add an SSE connection queue for a symbol"""
    active_sse_connections.setdefault(symbol,[]).append(queue)

async def remove_sse_connection(symbol: str, queue: asyncio.Queue):
    """Remove an SSE connection queue for a symbol"""
    if symbol in active_sse_connections:
        try:
            active_sse_connections[symbol].remove(queue)
            if not active_sse_connections[symbol]:
                del active_sse_connections[symbol]
        except ValueError:
            pass  # Queue not in list



### --- websocket handling ---
async def connect_to_websocket(
    websocket = WebSocketManager,
    uri = None,output_queue=None,
    **kwargs
    ):
    """Connect to the WebSocketManager and return it started"""
    ws_manager = websocket(uri = uri, output_queue=output_queue, **kwargs)
    try:
        await ws_manager.start()
        print("websocket manager started")
        return ws_manager
    except Exception as e:
        print(f"Error starting websocket manager: {e}")
        await ws_manager.stop()
        raise e

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager - startup and shutdown events"""
    # STARTUP: Initialize components when app starts
    logger.info("Starting application components...")

    # Initialize database manager
    db_connection = DuckDBConnection("data/stock_data.duckdb")
    app.state.db_manager = StockDataManager(db_connection=db_connection)

    # Websocket queue, max number of stocks
    shared_queue = asyncio.Queue(500)

    # Initialize historical data fetcher
    historical_fetcher = AlpacaHistoricalData(
        api_key=settings.ALPACA_API_KEY,
        api_secret=settings.ALPACA_API_SECRET
    )

    # Initialize data aggregator with all components
    app.state.data_aggregator = TradeDataAggregator(
        input_queue=shared_queue,
        broadcast_callback=broadcast_update,
        db_manager=app.state.db_manager,
        historical_fetcher=historical_fetcher
    )

    # Start processing task
    asyncio.create_task(app.state.data_aggregator.process_tick_queue())

    # Initialize WebSocket manager with the shared queue
    # "wss://stream.data.alpaca.markets/v2/test for FAKEPACA
    # "wss://stream.data.alpaca.markets/v2/iex"
    app.state.ws_manager = await connect_to_websocket(
        websocket = WebSocketManager,
        uri="wss://stream.data.alpaca.markets/v2/iex",
        output_queue=shared_queue
        )
    app.state.demo_ws_manager = await connect_to_websocket(
        websocket = WebSocketManager,
        uri="wss://stream.data.alpaca.markets/v2/test",
        output_queue=shared_queue
        )

    # Initialize SubscriptionManager (source of truth for subscriptions)
    app.state.subscription_manager = SubscriptionManager(
        subscribe_callback=app.state.ws_manager.subscribe,
        unsubscribe_callback=app.state.ws_manager.unsubscribe,
        on_handler_create_callback=app.state.data_aggregator.ensure_handler_exists
    )

    app.state.demo_subscription_manager = SubscriptionManager(
        subscribe_callback=app.state.demo_ws_manager.subscribe,
        unsubscribe_callback=app.state.demo_ws_manager.unsubscribe,
        on_handler_create_callback=app.state.data_aggregator.ensure_handler_exists
    )

    logger.info("SubscriptionManager initialized and wired")


    # Handle news after
    news_queue = asyncio.Queue(500)

    app.state.news_db_manager = NewsDataManager(db_connection=db_connection)
    app.state.news_ws = await connect_to_websocket(
        websocket = NewsWebsocket,
        uri = "wss://stream.data.alpaca.markets/v1beta1/news",
        output_queue=news_queue
        )

    asyncio.create_task(broadcast_news(news_queue))


    yield  # App runs here

    # SHUTDOWN: Clean up when app stops
    print("Shutting down application components...")
    if hasattr(app.state, 'data_aggregator'):
        await app.state.data_aggregator.shutdown()

    if hasattr(app.state, 'ws_manager'):
        await app.state.ws_manager.stop()

    if hasattr(app.state, 'demo_ws_manager'):
        await app.state.demo_ws_manager.stop()

    if hasattr(app.state, 'db_manager'):
        app.state.db_manager.close()

    if hasattr(app.state, 'news_ws'):
        await app.state.news_ws.stop()

app = FastAPI(
    title="Stock Market Data Service",
    description="Real-time stock market data and websocket service",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#app.include_router(subscription_router)

# Dependency injection functions
def get_ws_manager():
    """Get WebSocket manager from app state"""
    return app.state.ws_manager

def get_demo_ws_manager():
    """Get demo WebSocket manager from app state"""
    return app.state.demo_ws_manager

def get_data_aggregator():
    """Get data aggregator from app state"""
    return app.state.data_aggregator

def get_db_manager():
    """Get database manager from app state"""
    return app.state.db_manager

def get_subscription_manager():
    """Get subscription manager from app state"""
    return app.state.subscription_manager

def get_demo_subscription_manager():
    """Get demo subscription manager from app state"""
    return app.state.demo_subscription_manager

@app.get("/health")
def health_check():
    """Check if application is running"""
    return {"status": "healthy", "service": "stock-service", "environment": "production"}

@app.get("/ws_manager/status")
async def status(ws_manager: WebSocketManager = Depends(get_ws_manager)):
    """Check status of ws_manager"""
    output = await ws_manager.log_current_status()
    return {"message":f"{output}"}

@app.get("/ws_manager/{symbol}")
async def subscribe_to_symbol(
    symbol: str,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(get_demo_subscription_manager)
):
    """Subscribe to symbol stock data via SubscriptionManager"""
    # Use demo manager for FAKEPACA, otherwise use production manager
    manager = demo_subscription_manager if symbol == "FAKEPACA" else subscription_manager

    if manager is None:
        return {"message": "Subscription manager is not running", "status": "error"}

    try:
        # SubscriptionManager orchestrates: StockHandler creation + WebSocket subscription
        success = await manager.add_user_subscription(user_id=123, symbol=symbol, subscription_type='trades')

        if success:
            return {"message": "Subscribed to symbol successfully", "status": "subscribed", "symbol": symbol}
        else:
            return {"message": f"Failed to subscribe to {symbol}", "status": "error"}
    except Exception as e:
        logger.error("Subscription error for %s: %s", symbol, e)
        return {"message": f"Failed to subscribe to {symbol}: {str(e)}", "status": "error"}

@app.get("/ws_manager/close/{symbol}")
async def unsubscribe_to_symbol(
    symbol: str,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(get_demo_subscription_manager)
):
    """Unsubscribe from symbol stock data via SubscriptionManager"""
    # Use demo manager for FAKEPACA, otherwise use production manager
    manager = demo_subscription_manager if symbol == "FAKEPACA" else subscription_manager

    if manager is None:
        return {"message": "Subscription manager is not running", "status": "not_running"}

    try:
        success = await manager.remove_user_subscription(user_id=123, symbol=symbol, subscription_type='trades')

        if success:
            return {
                "message": "Unsubscribed from symbol successfully",
                "status": "unsubscribed",
                "symbol": symbol,
            }
        else:
            return {"message": f"Failed to unsubscribe from {symbol}", "status": "error"}
    except Exception as e:
        logger.error("Unsubscription error for %s: %s", symbol, e)
        return {"message": f"Failed to unsubscribe from {symbol}: {str(e)}", "status": "error"}

# Data Aggregator Endpoints
@app.get("/aggregator/status")
async def get_aggregator_status(
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator)
):
    """Get status of the data aggregator"""
    if data_aggregator is None:
        return {"status": "stopped", "message": "Data aggregator is not running"}

    return {
        "status": "running",
        "symbols_tracked": data_aggregator.get_all_symbols(),
        "queue_size": data_aggregator.queue.qsize()
    }

@app.get("/aggregator/symbols")
async def get_tracked_symbols(
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator)
):
    """Get all symbols being tracked by the aggregator"""
    if data_aggregator is None:
        return {"error": "Data aggregator is not running"}

    return {"symbols": data_aggregator.get_all_symbols()}

@app.get("/aggregator/data/{symbol}")
async def get_symbol_data(
    symbol: str,
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator)
):
    """Get OHLCV data for a specific symbol"""
    if data_aggregator is None:
        return {"error": "Data aggregator is not running"}

    stock_handler = data_aggregator.get_stock_handler(symbol.upper())
    if stock_handler is None:
        return {"error": f"No data found for symbol {symbol}"}

    return {
        "symbol": symbol.upper(),
        "candle_data": stock_handler.candle_data
    }

@app.get("/aggregator/data")
async def get_all_aggregated_data(
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator)
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
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator)
):
    """Stream real-time OHLCV data for a symbol via SSE"""
    symbol = symbol.upper()

    # Check if data aggregator is running
    if data_aggregator is None:
        raise HTTPException(status_code=503, detail="Data aggregator not running")

    # Check if symbol is already being tracked (has active WebSocket subscription)
    if symbol not in data_aggregator.get_all_symbols():
        raise HTTPException(
            status_code=400,
            detail=f"Symbol {symbol} not subscribed. Please subscribe via WebSocket first."
        )

    # Create SSE queue for this connection
    sse_queue = asyncio.Queue(maxsize=10)
    await add_sse_connection(symbol, sse_queue)

    # Send initial data immediately (full snapshot)
    stock_handler = data_aggregator.get_stock_handler(symbol)
    if stock_handler and stock_handler.candle_data:
        initial_data = {
            "symbol": symbol,
            "candles": stock_handler.candle_data,
            "update_timestamp": datetime.now(timezone.utc).isoformat(),
            "is_initial": True
        }
        await sse_queue.put(initial_data)
        # Mark this queue as initialized
        sse_queue._initialized = True

    async def event_stream():
        try:
            while True:
                # Wait for updates from StockHandler via broadcast
                update_data = await sse_queue.get()
                yield f"data: {json.dumps(update_data)}\n\n"
        except asyncio.CancelledError:
            # Clean up connection when client disconnects
            await remove_sse_connection(symbol, sse_queue)
            raise
        except Exception as e:
            # Clean up on any error
            await remove_sse_connection(symbol, sse_queue)
            raise e

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# Database Management Endpoints
@app.get("/database/stats")
async def get_database_stats(
    db_manager: StockDataManager = Depends(get_db_manager)
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
                    "last_updated": str(row[4])
                }
                for row in stats
            ],
            "total_symbols": len(stats)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e

@app.get("/database/export/{symbol}")
async def export_symbol_data(
    symbol: str,
    db_manager: StockDataManager = Depends(get_db_manager)
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
    db_manager: StockDataManager = Depends(get_db_manager)
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
        "supported_resolutions": ["1"]  # Only 1-minute bars for now
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
    db_manager: StockDataManager = Depends(get_db_manager)
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

        from_timestamp = from_dt.isoformat().replace('+00:00', 'Z')
        to_timestamp = to_dt.isoformat().replace('+00:00', 'Z')

        # Query database
        candles = db_manager.get_candles_by_time_range(
            symbol.upper(),
            from_timestamp,
            to_timestamp
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
            "v": []   # volume
        }

        for timestamp, candle in sorted(candles.items()):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            tv_bars["t"].append(int(dt.timestamp()))
            tv_bars["o"].append(candle["open"])
            tv_bars["h"].append(candle["high"])
            tv_bars["l"].append(candle["low"])
            tv_bars["c"].append(candle["close"])
            tv_bars["v"].append(candle["volume"])

        logger.info(
            "Returned %s bars for %s from %s to %s",
            len(tv_bars['t']), symbol, from_timestamp, to_timestamp
        )
        return tv_bars

    except Exception as e:
        logger.error("TradingView history error for %s: %s", symbol, e)
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}") from e


@app.get("/news/stream")
async def stream_news_data():
    """Stream news data via SSE"""
    n_queue = asyncio.Queue(maxsize=10)
    add_news_connection(n_queue)

    async def event_stream():
        try:
            while True:
                update_data = await n_queue.get()

                # Handle shutdown signal early
                if update_data is None:
                    logger.info("News Strem shutdown signal received")
                    break
                try:
                    update_data = NewsWebsocket.process_news_data(update_data)
                    yield f"data: {json.dumps(update_data)}\n\n"
                except (KeyError, ValueError) as e:
                    logger.warning("Invalid news data, skipping %s", e)
                    continue  # Skip this item, keep streaming
        except asyncio.CancelledError:
            logger.info("News stream cancelled by client disconnect")
            raise
        except Exception as e:
            logger.error("Unexpected error in news stream: %s", e, exc_info=True)
            raise
        finally:
            # Cleanup
            remove_news_connection(queue=n_queue)
            logger.debug("News Connection cleaned up ")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
