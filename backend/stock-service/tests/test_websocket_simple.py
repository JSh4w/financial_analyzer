"""Testing Websocket Functionality with finnhub API"""
import asyncio
import pytest
from app.stocks.websocket_manager import WebSocketManager
import logging

logging.basicConfig(level=logging.DEBUG)

@pytest.mark.asyncio
async def test_main(caplog):
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
        print("Queuing subscription for FAKEPACA, user 123")
        await ws_manager.enqueue_subscription("FAKEPACA", 123)

        # # Wait for it to process
        await asyncio.sleep(5)
        # # Log current status
        await ws_manager.log_current_status()

        #await ws_manager.enqueue_subscription("MSFT", 123)

        # # Keep running for a bit to see data
        # print("Listening fr data for 10 seconds...")
        await asyncio.sleep(0.5)

        await ws_manager.log_current_status()

        await asyncio.sleep(1)

        await ws_manager.enqueue_unsubscription("FAKEPACA", 123)

        await asyncio.sleep(1)

        await ws_manager.log_current_status()

        await asyncio.sleep(1)

        # The fixture will automatically check for ERROR logs after the test
        if errors := [f"{r.name}: {r.levelname}: {r.message}" 
                    for r in caplog.records if r.levelno >= logging.ERROR]:
            pytest.fail(f"Test failed due to ERROR logs: {errors}")

    finally:
        await ws_manager.stop()
