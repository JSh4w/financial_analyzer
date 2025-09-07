"""Utility functions for timing and more"""
import asyncio
import time
import functools
from datetime import datetime, timezone
from logging import getLogger

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
                    logger.info(f"{name} completed in {execution_time:.2f}ms, at {datetime.now(timezone.utc).isoformat()}")
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
                    logger.info(f"{name} completed in {execution_time:.2f}ms, at {datetime.now(timezone.utc).isoformat()}")
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    logger.error(f"{name} failed after {execution_time:.2f}ms: {e}")
                    raise
            return sync_wrapper
    return decorator
