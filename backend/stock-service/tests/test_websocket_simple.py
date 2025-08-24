#!/usr/bin/env python3
import pytest
import asyncio
import logging
from app.stocks.websocket_manager import WebSocketManager

# Setup logging
logging.basicConfig(level=logging.INFO)

@pytest.mark.asyncio
async def test_main():
    """Test for handling websocket and data storage - full integration test/ init for backend"""
    # Create WebSocket manager
    ws_manager = WebSocketManager()

    try:
        # Start the manager
        await ws_manager.start()
        print("WebSocket manager started")

        # # Wait a moment for connection
        await asyncio.sleep(1)

        # # Queue a subscription
        print("Queuing subscription for AAPL, user 123")
        await ws_manager.enqueue_subscription("AAPL", 123)

        # # Wait for it to process
        await asyncio.sleep(1)
        # # Log current status
        await ws_manager.log_current_status()

        await ws_manager.enqueue_subscription("MSFT", 123)

        # # Keep running for a bit to see data
        # print("Listening fr data for 10 seconds...")
        await asyncio.sleep(0.5)

        await ws_manager.log_current_status()

        await asyncio.sleep(1)

        await ws_manager.enqueue_unsubscription("AAPL", 123)

        await asyncio.sleep(1)

        await ws_manager.log_current_status()

        await asyncio.sleep(1)

    finally:
        await ws_manager.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Graceful shutdown completed")