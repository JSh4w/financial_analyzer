from datetime import datetime, timezone
from logging import getLogger

from app.auth import get_current_user_id
from app.database.subscription_manager import PersistentSubscriptionManager
from app.dependencies import (
    get_data_aggregator,
    get_demo_subscription_manager,
    get_persistent_subscription_manager,
    get_subscription_manager,
)
from app.stocks.data_aggregator import TradeDataAggregator
from app.stocks.subscription_manager import SubscriptionManager
from fastapi import APIRouter, Depends, HTTPException

logger = getLogger(__name__)
router = APIRouter(prefix="/subscriptions")


# Persistent Subscription Endpoints (New)
@router.post("/subscribe/{symbol}")
async def create_persistent_subscription(
    symbol: str,
    user_id: str = Depends(get_current_user_id),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(
        get_demo_subscription_manager
    ),
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    persistent_manager: PersistentSubscriptionManager = Depends(
        get_persistent_subscription_manager
    ),
):
    """
    Subscribe user to a symbol with persistent storage in database
    This combines database persistence with WebSocket subscription
    """
    symbol = symbol.upper()

    try:
        # Save to database (persistent)
        success = persistent_manager.subscribe_user(user_id, symbol)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to create persistent subscription"
            )

        # Check if we need to subscribe to Alpaca WebSocket
        if symbol not in data_aggregator.get_all_symbols():
            # First subscriber - create WebSocket subscription
            manager = (
                demo_subscription_manager
                if symbol == "FAKEPACA"
                else subscription_manager
            )

            if manager is None:
                raise HTTPException(
                    status_code=503, detail="Subscription manager not running"
                )

            ws_success = await manager.add_user_subscription(
                user_id=user_id, symbol=symbol, subscription_type="trades"
            )

            if not ws_success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to subscribe to market data for {symbol}",
                )

            logger.info(f"Subscribed to {symbol} on Alpaca for user {user_id}")

        subscriber_count = persistent_manager.get_symbol_subscriber_count(symbol)

        return {
            "status": "subscribed",
            "symbol": symbol,
            "subscriber_count": subscriber_count,
            "message": f"Successfully subscribed to {symbol}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create subscription for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/subscribe/{symbol}")
async def delete_persistent_subscription(
    symbol: str,
    user_id: str = Depends(get_current_user_id),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(
        get_demo_subscription_manager
    ),
    persistent_manager: PersistentSubscriptionManager = Depends(
        get_persistent_subscription_manager
    ),
):
    """
    Unsubscribe user from a symbol (marks as inactive in database)
    Only unsubscribes from Alpaca if no other users are watching the symbol
    """
    symbol = symbol.upper()

    try:
        # Mark as inactive in database
        persistent_manager.unsubscribe_user(user_id, symbol)

        # Check if we should unsubscribe from Alpaca
        if persistent_manager.should_unsubscribe_from_alpaca(symbol):
            manager = (
                demo_subscription_manager
                if symbol == "FAKEPACA"
                else subscription_manager
            )

            if manager:
                await manager.remove_user_subscription(
                    user_id=user_id, symbol=symbol, subscription_type="trades"
                )
                logger.info(f"Unsubscribed from {symbol} on Alpaca (no active users)")

        remaining = persistent_manager.get_symbol_subscriber_count(symbol)

        return {
            "status": "unsubscribed",
            "symbol": symbol,
            "remaining_subscribers": remaining,
            "message": f"Successfully unsubscribed from {symbol}",
        }

    except Exception as e:
        logger.error(f"Failed to unsubscribe from {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user_subscriptions")
async def get_user_persistent_subscriptions(
    user_id: str = Depends(get_current_user_id),
    persistent_manager: PersistentSubscriptionManager = Depends(
        get_persistent_subscription_manager
    ),
):
    """
    Get all active subscriptions for the current user (their watchlist)
    """
    try:
        symbols = persistent_manager.get_user_subscriptions(user_id)

        return {"symbols": symbols, "count": len(symbols)}

    except Exception as e:
        logger.error(f"Failed to get subscriptions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot/{symbol}")
async def get_symbol_snapshot(
    symbol: str,
    _: str = Depends(get_current_user_id),
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
):
    """
    Get current snapshot of all candles for a symbol
    Used by SSE service to send initial data to clients
    """
    symbol = symbol.upper()

    if data_aggregator is None:
        raise HTTPException(status_code=503, detail="Data aggregator not running")

    handler = data_aggregator.get_stock_handler(symbol)
    if not handler:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not subscribed")

    return {
        "symbol": symbol,
        "candles": handler.candle_data,
        "update_timestamp": datetime.now(timezone.utc).isoformat(),
        "is_initial": True,
    }
