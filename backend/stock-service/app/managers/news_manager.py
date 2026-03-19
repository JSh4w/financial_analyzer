"""Functions relating for handling news data"""

import asyncio
from collections import deque
from logging import getLogger
from typing import Deque, List

logger = getLogger(__name__)

# Since each person consumes a queue, we need one per news connection
active_news_connections: List[asyncio.Queue] = []
news_cache: Deque[str] = deque(maxlen=100)


### --- News broadcast handling ---
async def broadcast_news(news_queue: asyncio.Queue):
    """Broadcast news data to the frontend"""
    while True:
        item = await news_queue.get()
        if item is None:
            break  # sentinal

        news_cache.append(item)

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
    queue.put_nowait(news_cache)


def remove_news_connection(queue: asyncio.Queue):
    """Remove user for news information"""
    active_news_connections.remove(queue)
