import asyncio
from logging import getLogger
from typing import Dict

from app.database.subscription_manager import PersistentSubscriptionManager
from app.stocks.subscription_manager import (
    SubscriptionManager,  # For users to interact with websocket
)
from app.utils import time_function  # Timing a function request

logger = getLogger(__name__)

# SSE connection management
active_sse_connections: Dict[str, Dict[str, asyncio.Queue[Dict]]] = {}


### --- Server Side Event Connection Handling ---
@time_function("broadcast_update")
def broadcast_update(update_data: dict):
    """Broadcast update to all SSE connections for a symbol"""
    symbol = update_data.get("symbol")
    is_initial = update_data.get("is_initial", False)

    if symbol and symbol in active_sse_connections:
        user_connections = active_sse_connections[symbol]
        connection_count = len(user_connections)

        # Remove any dead connections while broadcasting
        dead_users = []
        successful_broadcasts = 0

        for user_id, queue in user_connections.items():
            try:
                # For delta updates, only send to already-initialized connections
                # For initial updates, send to all connections
                if is_initial or hasattr(queue, "_initialized"):
                    queue.put_nowait(update_data)
                    successful_broadcasts += 1
                    # Mark queue as initialized after first message
                    if is_initial:
                        queue._initialized = True  # type: ignore[reportAttributeAccessIssue] pylint: disable=protected-access
            except asyncio.QueueFull:
                # Mark for removal if queue is full
                dead_users.append(user_id)
                logger.warning(
                    "SSE queue full for %s user %s, removing connection",
                    symbol,
                    user_id,
                )
            except Exception as e:
                # Mark for removal if any other error
                dead_users.append(user_id)
                logger.warning(
                    "SSE broadcast error for %s user %s: %s", symbol, user_id, e
                )

        # Clean up dead connections
        for dead_user in dead_users:
            try:
                del active_sse_connections[symbol][dead_user]
            except KeyError:
                pass

        logger.debug(
            "Broadcasted to %s/%s SSE connections for %s",
            successful_broadcasts,
            connection_count,
            symbol,
        )
    else:
        logger.debug("No SSE connections for symbol %s", symbol)


async def add_sse_connection(
    symbol: str, user_id: str, queue: asyncio.Queue
) -> asyncio.Queue | None:
    """
    Add an SSE connection queue for a symbol and user.
    Returns the old queue if user already had a connection (for cleanup).
    """
    if symbol not in active_sse_connections:
        active_sse_connections[symbol] = {}

    old_queue = active_sse_connections[symbol].get(user_id)
    active_sse_connections[symbol][user_id] = queue

    if old_queue:
        logger.info(
            "Replacing existing SSE connection for user %s on symbol %s",
            user_id,
            symbol,
        )

    return old_queue


async def remove_sse_connection(
    symbol: str,
    user_id: str,
    persistent_manager: PersistentSubscriptionManager,
    subscription_manager: SubscriptionManager,
    demo_subscription_manager: SubscriptionManager,
):
    """
    Remove an SSE connection for a symbol and user.
    If no SSE connections AND no permanent subscribers remain, unsubscribe from Alpaca.
    """
    if symbol in active_sse_connections:
        try:
            # Remove this user's connection
            if user_id in active_sse_connections[symbol]:
                del active_sse_connections[symbol][user_id]

            sse_connections_remaining = len(active_sse_connections.get(symbol, {}))

            if not active_sse_connections[symbol]:
                del active_sse_connections[symbol]
                sse_connections_remaining = 0

            # Check if we should unsubscribe from Alpaca WebSocket
            if persistent_manager and subscription_manager:
                permanent_subscribers = persistent_manager.get_symbol_subscriber_count(
                    symbol
                )

                logger.debug(
                    f"SSE closed for {symbol} (user {user_id}): {sse_connections_remaining} SSE remaining, "
                    f"{permanent_subscribers} permanent subscribers"
                )

                # Only unsubscribe if NO SSE connections AND NO permanent subscribers
                if sse_connections_remaining == 0 and permanent_subscribers == 0:
                    manager = (
                        demo_subscription_manager
                        if symbol == "FAKEPACA"
                        else subscription_manager
                    )
                    if manager:
                        try:
                            await manager.remove_user_subscription(
                                user_id=user_id,
                                symbol=symbol,
                                subscription_type="trades",
                            )
                            logger.info(
                                f"Unsubscribed from {symbol} on Alpaca (no active users)"
                            )
                        except Exception as e:
                            logger.error(f"Failed to unsubscribe from {symbol}: {e}")

        except KeyError:
            pass  # User not in connections
