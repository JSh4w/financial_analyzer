import os
import json
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from symtable import Symbol
from typing import Dict, List
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import Settings
from app.stocks.websocket_manager import WebSocketManager
from app.stocks.data_aggregator import TradeDataAggregator
from app.stocks.market_data_handler import TradeDataHandler
#from app.subscription_routes import router as subscription_router
from core.logging import setup_logging


setup_logging(level="DEBUG")

load_dotenv()
latest_data = {"message": "No data received yet", "timestamp": None}

settings = Settings()

# Global instances
GLOBAL_WS_MANAGER = None
GLOBAL_DATA_AGGREGATOR = None

# SSE connection management
active_sse_connections: Dict[str, List[asyncio.Queue]] = {}

async def add_sse_connection(symbol: str, queue: asyncio.Queue):
    """Add an SSE connection queue for a symbol"""
    if symbol not in active_sse_connections:
        active_sse_connections[symbol] = []
    active_sse_connections[symbol].append(queue)

async def remove_sse_connection(symbol: str, queue: asyncio.Queue):
    """Remove an SSE connection queue for a symbol"""
    if symbol in active_sse_connections:
        try:
            active_sse_connections[symbol].remove(queue)
            if not active_sse_connections[symbol]:
                del active_sse_connections[symbol]
        except ValueError:
            pass  # Queue not in list

def broadcast_update(update_data: dict):
    """Broadcast update to all SSE connections for a symbol"""
    symbol = update_data.get("symbol")
    if symbol and symbol in active_sse_connections:
        # Remove any dead connections while broadcasting
        dead_queues = []
        for queue in active_sse_connections[symbol]:
            try:
                # Use put_nowait to avoid blocking
                queue.put_nowait(update_data)
            except asyncio.QueueFull:
                # Mark for removal if queue is full
                dead_queues.append(queue)
            except Exception:
                # Mark for removal if any other error
                dead_queues.append(queue)
        
        # Clean up dead connections
        for dead_queue in dead_queues:
            try:
                active_sse_connections[symbol].remove(dead_queue)
            except ValueError:
                pass

async def connect_to_websocket_manager(output_queue=None):
    """Connect to the WebSocketManager and return it started"""
    ws_manager = WebSocketManager(output_queue=output_queue)
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
    global GLOBAL_WS_MANAGER, GLOBAL_DATA_AGGREGATOR

    # STARTUP: Initialize components when app starts
    print("Starting application components...")
    
    # Create shared queue for WebSocket -> Aggregator communication
    shared_queue = asyncio.Queue(500)
    
    # Initialize data aggregator with the shared queue and broadcast callback
    GLOBAL_DATA_AGGREGATOR = TradeDataAggregator(input_queue=shared_queue, broadcast_callback=broadcast_update)
    
    # Start processing task
    asyncio.create_task(GLOBAL_DATA_AGGREGATOR.process_tick_queue())
    
    # Initialize WebSocket manager with the shared queue
    GLOBAL_WS_MANAGER = await connect_to_websocket_manager(output_queue=shared_queue)

    yield  # App runs here

    # SHUTDOWN: Clean up when app stops
    print("Shutting down application components...")
    if GLOBAL_DATA_AGGREGATOR:
        await GLOBAL_DATA_AGGREGATOR.shutdown()
        GLOBAL_DATA_AGGREGATOR = None
    
    if GLOBAL_WS_MANAGER:
        await GLOBAL_WS_MANAGER.stop()
        GLOBAL_WS_MANAGER = None

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

@app.get("/")
def root():
    return {"message": "Stock Market Data Service", "service": "stock-service"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "stock-service", "environment": "production"}

@app.get("/apple")
def get_stock_data():
    return latest_data

@app.post("/test_post")
def test_post():
    return {"message": "Test post successful"}

@app.get("/ws_manager/{symbol}")
async def subscribe_to_apple(symbol : str):
    """Subscribe to symbol stock data"""
    global GLOBAL_WS_MANAGER

    if GLOBAL_WS_MANAGER is None:
        return {"message": "WebSocket manager is not running", "status": "error"}

    try:
        await GLOBAL_WS_MANAGER.enqueue_subscription(symbol, 123)
        return {"message": "Subscribed to AAPL successfully", "status": "subscribed", "symbol": symbol}
    except Exception as e:
        return {"message": f"Failed to subscribe to {symbol}: {str(e)}", "status": "error"}

@app.get("/ws_manager/close")
async def unsubscribe_from_apple():
    """Unsubscribe from AAPL stock data"""
    global GLOBAL_WS_MANAGER

    if GLOBAL_WS_MANAGER is None:
        return {"message": "WebSocket manager is not running", "status": "not_running"}

    try:
        await GLOBAL_WS_MANAGER.enqueue_unsubscription("AAPL", 123)
        return {"message": "Unsubscribed from AAPL successfully", "status": "unsubscribed", "symbol": "AAPL"}
    except Exception as e:
        return {"message": f"Failed to unsubscribe from AAPL: {str(e)}", "status": "error"}

@app.get("/ws_manager/status")
async def get_websocket_manager_status():
    """Get the status of the WebSocket manager"""
    global GLOBAL_WS_MANAGER

    if GLOBAL_WS_MANAGER is None:
        return {"status": "stopped", "message": "WebSocket manager is not running"}

    try:
        # Get current data from the manager
        storage_data = GLOBAL_WS_MANAGER.data_handler.storage if hasattr(GLOBAL_WS_MANAGER, 'data_handler') else {}
        return {
            "status": "running",
            "message": "WebSocket manager is active",
            "data": storage_data
        }
    except Exception as e:
        return {"status": "error", "message": f"Error getting status: {str(e)}"}

@app.get("/ws_manager/data")
async def get_websocket_data():
    """Get current data from the WebSocket manager"""
    global GLOBAL_WS_MANAGER

    if GLOBAL_WS_MANAGER is None:
        return {"error": "WebSocket manager is not running"}

    try:
        return GLOBAL_WS_MANAGER.data_handler.storage
    except Exception as e:
        return {"error": f"Failed to get data: {str(e)}"}

# Data Aggregator Endpoints
@app.get("/aggregator/status")
async def get_aggregator_status():
    """Get status of the data aggregator"""
    global GLOBAL_DATA_AGGREGATOR
    
    if GLOBAL_DATA_AGGREGATOR is None:
        return {"status": "stopped", "message": "Data aggregator is not running"}
    
    return {
        "status": "running",
        "symbols_tracked": GLOBAL_DATA_AGGREGATOR.get_all_symbols(),
        "queue_size": GLOBAL_DATA_AGGREGATOR.queue.qsize()
    }

@app.get("/aggregator/symbols")
async def get_tracked_symbols():
    """Get all symbols being tracked by the aggregator"""
    global GLOBAL_DATA_AGGREGATOR
    
    if GLOBAL_DATA_AGGREGATOR is None:
        return {"error": "Data aggregator is not running"}
    
    return {"symbols": GLOBAL_DATA_AGGREGATOR.get_all_symbols()}

@app.get("/aggregator/data/{symbol}")
async def get_symbol_data(symbol: str):
    """Get OHLCV data for a specific symbol"""
    global GLOBAL_DATA_AGGREGATOR
    
    if GLOBAL_DATA_AGGREGATOR is None:
        return {"error": "Data aggregator is not running"}
    
    stock_handler = GLOBAL_DATA_AGGREGATOR.get_stock_handler(symbol.upper())
    if stock_handler is None:
        return {"error": f"No data found for symbol {symbol}"}
    
    return {
        "symbol": symbol.upper(),
        "candle_data": stock_handler.candle_data
    }

@app.get("/aggregator/data")
async def get_all_aggregated_data():
    """Get OHLCV data for all tracked symbols"""
    global GLOBAL_DATA_AGGREGATOR
    
    if GLOBAL_DATA_AGGREGATOR is None:
        return {"error": "Data aggregator is not running"}
    
    all_data = {}
    for symbol in GLOBAL_DATA_AGGREGATOR.get_all_symbols():
        stock_handler = GLOBAL_DATA_AGGREGATOR.get_stock_handler(symbol)
        if stock_handler:
            all_data[symbol] = stock_handler.candle_data
    
    return {"data": all_data}

# SSE Streaming Endpoints
@app.get("/stream/{symbol}")
async def stream_stock_data(symbol: str):
    """Stream real-time OHLCV data for a symbol via SSE"""
    global GLOBAL_WS_MANAGER, GLOBAL_DATA_AGGREGATOR
    
    symbol = symbol.upper()
    
    # Check if data aggregator is running
    if GLOBAL_DATA_AGGREGATOR is None:
        raise HTTPException(status_code=503, detail="Data aggregator not running")
    
    # Check if symbol is already being tracked (has active WebSocket subscription)
    if symbol not in GLOBAL_DATA_AGGREGATOR.get_all_symbols():
        raise HTTPException(
            status_code=400, 
            detail=f"Symbol {symbol} not subscribed. Please subscribe via WebSocket first."
        )
    
    # Create SSE queue for this connection
    sse_queue = asyncio.Queue(maxsize=10)
    await add_sse_connection(symbol, sse_queue)
    
    # Send initial data immediately
    stock_handler = GLOBAL_DATA_AGGREGATOR.get_stock_handler(symbol)
    if stock_handler and stock_handler.candle_data:
        initial_data = {
            "symbol": symbol,
            "candles": stock_handler.candle_data,
            "update_timestamp": asyncio.get_event_loop().time()
        }
        await sse_queue.put(initial_data)
    
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
            raise
    
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