#!/usr/bin/env python3
import asyncio
import logging
from app.websocket_manager import WebSocketManager

# Setup logging
logging.basicConfig(level=logging.INFO)

async def main():
    """Test for handling websocket and data storage - full integration test/ init for backend"""
    # Create WebSocket manager
    temp_storage = {}
    ws_manager = WebSocketManager(storage_dict=temp_storage)

    try:
        # Start the manager
        await ws_manager.start()
        print("WebSocket manager started")

        # # Wait a moment for connection
        await asyncio.sleep(2)

        # # Queue a subscription
        print("Queuing subscription for AAPL, user 123")
        await ws_manager.enqueue_subscription("AAPL", 123)

        # # Wait for it to process
        await asyncio.sleep(2)

        print(ws_manager.data_handler.storage)

        await asyncio.sleep(2)

        # # Log current status
        await ws_manager.log_current_status()

        await ws_manager.enqueue_subscription("MSFT", 123)


        # # Keep running for a bit to see data
        # print("Listening for data for 10 seconds...")
        await asyncio.sleep(5)
        print(ws_manager.data_handler.storage)

        await ws_manager.log_current_status()

        await asyncio.sleep(2)

        await ws_manager.enqueue_unsubscription("AAPL", 123)

        await asyncio.sleep(2)

        await asyncio.sleep(5)

        ws_manager.data_handler.pickle_storage()

        await asyncio.sleep(2)
        await ws_manager.log_current_status()

        await asyncio.sleep(2)

    finally:
        await ws_manager.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Graceful shutdown completed")