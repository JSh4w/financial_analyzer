import os
import json
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.stocks.websocket_manager import WebSocketManager
#from app.subscription_routes import router as subscription_router
from core.logging import setup_logging


setup_logging(level="DEBUG")

load_dotenv()
latest_data = {"message": "No data received yet", "timestamp": None}

settings = Settings()

# Global WebSocket manager instance
GLOBAL_WS_MANAGER = None

async def connect_to_websocket_manager():
    """Connect to the WebSocketManager and return it started"""
    ws_manager = WebSocketManager()
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
    global GLOBAL_WS_MANAGER

    # STARTUP: Initialize WebSocket manager when app starts
    print("Starting WebSocket manager on app startup...")
    GLOBAL_WS_MANAGER = await connect_to_websocket_manager()

    yield  # App runs here

    # SHUTDOWN: Clean up when app stops
    print("Shutting down WebSocket manager...")
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

@app.get("/ws_manager")
async def subscribe_to_apple():
    """Subscribe to AAPL stock data"""
    global GLOBAL_WS_MANAGER

    if GLOBAL_WS_MANAGER is None:
        return {"message": "WebSocket manager is not running", "status": "error"}

    try:
        await GLOBAL_WS_MANAGER.enqueue_subscription("AAPL", 123)
        return {"message": "Subscribed to AAPL successfully", "status": "subscribed", "symbol": "AAPL"}
    except Exception as e:
        return {"message": f"Failed to subscribe to AAPL: {str(e)}", "status": "error"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)