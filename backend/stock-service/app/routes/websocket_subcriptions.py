"""Routes for managing WebSocket subscriptions to stock data"""

from logging import getLogger

from app.auth import get_current_user_id
from app.dependencies import (
    get_demo_subscription_manager,
    get_subscription_manager,
    get_ws_manager,
)
from app.stocks.subscription_manager import SubscriptionManager
from fastapi import APIRouter, Depends

logger = getLogger(__name__)

router = APIRouter(prefix="/ws_manager")


@router.get("/status")
async def status(
    ws_manager: WebSocketManager = Depends(get_ws_manager),
    _: str = Depends(get_current_user_id),
):
    """Check status of ws_manager"""
    output = await ws_manager.log_current_status()
    return {"message": f"{output}"}


@router.get("/{symbol}")
async def subscribe_to_symbol(
    symbol: str,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(
        get_demo_subscription_manager
    ),
    user_id: str = Depends(get_current_user_id),
):
    """Subscribe to symbol stock data via SubscriptionManager"""
    # Use demo manager for FAKEPACA, otherwise use production manager
    manager = (
        demo_subscription_manager if symbol == "FAKEPACA" else subscription_manager
    )

    if manager is None:
        return {"message": "Subscription manager is not running", "status": "error"}

    try:
        # SubscriptionManager orchestrates: StockHandler creation + WebSocket subscription
        success = await manager.add_user_subscription(
            user_id=user_id, symbol=symbol, subscription_type="trades"
        )

        if success:
            return {
                "message": "Subscribed to symbol successfully",
                "status": "subscribed",
                "symbol": symbol,
            }

        return {"message": f"Failed to subscribe to {symbol}", "status": "error"}
    except Exception as e:
        logger.error("Subscription error for %s: %s", symbol, e)
        return {
            "message": f"Failed to subscribe to {symbol}: {str(e)}",
            "status": "error",
        }


@router.get("/close/{symbol}")
async def unsubscribe_to_symbol(
    symbol: str,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    demo_subscription_manager: SubscriptionManager = Depends(
        get_demo_subscription_manager
    ),
    user_id: str = Depends(get_current_user_id),
):
    """Unsubscribe from symbol stock data via SubscriptionManager"""
    # Use demo manager for FAKEPACA, otherwise use production manager
    manager = (
        demo_subscription_manager if symbol == "FAKEPACA" else subscription_manager
    )

    if manager is None:
        return {
            "message": "Subscription manager is not running",
            "status": "not_running",
        }

    try:
        success = await manager.remove_user_subscription(
            user_id=user_id, symbol=symbol, subscription_type="trades"
        )

        if success:
            return {
                "message": "Unsubscribed from symbol successfully",
                "status": "unsubscribed",
                "symbol": symbol,
            }
        else:
            return {
                "message": f"Failed to unsubscribe from {symbol}",
                "status": "error",
            }
    except Exception as e:
        logger.error("Unsubscription error for %s: %s", symbol, e)
        return {
            "message": f"Failed to unsubscribe from {symbol}: {str(e)}",
            "status": "error",
        }
