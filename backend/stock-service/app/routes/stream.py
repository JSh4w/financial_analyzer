"""SSE streaming endpoints for real-time stock and news data"""

import asyncio
import json
from datetime import datetime, timezone
from logging import getLogger

from app.auth import decode_jwt_token
from app.database.subscription_manager import PersistentSubscriptionManager
from app.dependencies import (
    get_data_aggregator,
    get_demo_subscription_manager,
    get_persistent_subscription_manager,
    get_subscription_manager,
)
from app.managers.news_manager import add_news_connection, remove_news_connection
from app.managers.sse_manager import add_sse_connection, remove_sse_connection
from app.stocks.data_aggregator import TradeDataAggregator
from app.stocks.news_websocket import NewsWebsocket
from app.stocks.subscription_manager import SubscriptionManager
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

logger = getLogger(__name__)
router = APIRouter()


@router.get("/stream/{symbol}")
async def stream_stock_data(
    symbol: str,
    token: str,
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    persistent_manager: PersistentSubscriptionManager = Depends(
        get_persistent_subscription_manager
    ),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(
        get_demo_subscription_manager
    ),
):
    """Stream real-time OHLCV data for a symbol via SSE"""
    # Validate token from query parameter (EventSource doesn't support headers)
    user = decode_jwt_token(token)
    user_id = user.sub

    symbol = symbol.upper()

    if data_aggregator is None:
        raise HTTPException(status_code=503, detail="Data aggregator not running")

    if symbol not in data_aggregator.get_all_symbols():
        raise HTTPException(
            status_code=400,
            detail=f"Symbol {symbol} not subscribed. Please subscribe via WebSocket first.",
        )

    sse_queue = asyncio.Queue(maxsize=10)
    old_queue = await add_sse_connection(symbol, user_id, sse_queue)

    if old_queue:
        try:
            old_queue.put_nowait({"_terminate": True})
        except asyncio.QueueFull:
            pass

    stock_handler = data_aggregator.get_stock_handler(symbol)
    if stock_handler and stock_handler.candle_data:
        initial_data = {
            "symbol": symbol,
            "candles": stock_handler.candle_data,
            "update_timestamp": datetime.now(timezone.utc).isoformat(),
            "is_initial": True,
        }
        await sse_queue.put(initial_data)
        sse_queue._initialized = True  # type: ignore[reportAttributeAccessIssue]

    async def event_stream():
        try:
            while True:
                update_data = await sse_queue.get()

                if isinstance(update_data, dict) and update_data.get("_terminate"):
                    logger.info(
                        "SSE connection replaced for user %s on %s", user_id, symbol
                    )
                    break

                yield f"data: {json.dumps(update_data)}\n\n"
        except asyncio.CancelledError:
            logger.info("Stock stream cancelled for user %s on %s", user_id, symbol)
        except Exception as e:
            logger.error("Stock stream error for user %s on %s: %s", user_id, symbol, e)
        finally:
            await remove_sse_connection(
                symbol,
                user_id,
                persistent_manager=persistent_manager,
                subscription_manager=subscription_manager,
                demo_subscription_manager=demo_subscription_manager,
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/news/stream")
async def stream_news_data(token: str):
    """Stream news data via SSE"""
    try:
        user = decode_jwt_token(token)
        user_id = user.sub  # noqa: F841
    except HTTPException as e:
        logger.warning("News stream auth failed: %s", e.detail)
        raise HTTPException(
            status_code=401, detail="Invalid token for news stream"
        ) from e

    n_queue = asyncio.Queue(maxsize=10)
    add_news_connection(n_queue)

    async def event_stream():
        try:
            while True:
                update_data = await n_queue.get()

                if update_data is None:
                    logger.info("News stream shutdown signal received")
                    break
                try:
                    update_data = NewsWebsocket.process_news_data(update_data)
                    yield f"data: {json.dumps(update_data)}\n\n"
                except (KeyError, ValueError) as e:
                    logger.warning("Invalid news data, skipping: %s", e)
                    continue
        except asyncio.CancelledError:
            logger.info("News stream cancelled by client disconnect")
        except Exception as e:
            logger.error("Unexpected error in news stream: %s", e)
        finally:
            remove_news_connection(queue=n_queue)
            logger.debug("News connection cleaned up")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
