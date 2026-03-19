"""Utility functions for timing and more"""

import asyncio
import functools
import time
from datetime import datetime, timezone
from logging import getLogger

from app.stocks.websocket_manager import WebSocketManager

logger = getLogger(__name__)


# Timing decorator
def time_function(func_name: str = None):
    """Decorator to time function execution"""

    def decorator(func):
        name = func_name or func.__name__

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    execution_time = (time.time() - start_time) * 1000
                    logger.info(
                        f"{name} completed in {execution_time:.2f}ms, at {datetime.now(timezone.utc).isoformat()}"
                    )
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    logger.error(f"{name} failed after {execution_time:.2f}ms: {e}")
                    raise

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = (time.time() - start_time) * 1000
                    logger.info(
                        f"{name} completed in {execution_time:.2f}ms, at {datetime.now(timezone.utc).isoformat()}"
                    )
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    logger.error(f"{name} failed after {execution_time:.2f}ms: {e}")
                    raise

            return sync_wrapper

    return decorator


### --- websocket handling ---
async def connect_and_start_websocket(
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
