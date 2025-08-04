from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from app.stocks.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

class SubscriptionRequest(BaseModel):
    symbol: str

class SubscriptionResponse(BaseModel):
    symbol: str
    status: str
    message: str

class SubscriptionsListResponse(BaseModel):
    subscriptions: List[str]
    total: int

@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe_to_symbol(request: SubscriptionRequest):
    """Subscribe to a stock symbol for real-time data"""
    try:
        symbol = request.symbol.upper()
        await websocket_manager.subscribe(symbol)
        
        return SubscriptionResponse(
            symbol=symbol,
            status="success",
            message=f"Successfully subscribed to {symbol}"
        )
    except Exception as e:
        logger.error(f"Failed to subscribe to {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to subscribe: {str(e)}")

@router.delete("/unsubscribe", response_model=SubscriptionResponse)
async def unsubscribe_from_symbol(request: SubscriptionRequest):
    """Unsubscribe from a stock symbol"""
    try:
        symbol = request.symbol.upper()
        await websocket_manager.unsubscribe(symbol)
        
        return SubscriptionResponse(
            symbol=symbol,
            status="success",
            message=f"Successfully unsubscribed from {symbol}"
        )
    except Exception as e:
        logger.error(f"Failed to unsubscribe from {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe: {str(e)}")

@router.get("/list", response_model=SubscriptionsListResponse)
async def get_subscriptions():
    """Get list of current subscriptions"""
    try:
        subscriptions = await websocket_manager.get_subscriptions()
        return SubscriptionsListResponse(
            subscriptions=list(subscriptions),
            total=len(subscriptions)
        )
    except Exception as e:
        logger.error(f"Failed to get subscriptions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get subscriptions: {str(e)}")

@router.get("/status")
async def get_connection_status():
    """Get WebSocket connection status"""
    return {
        "connected": websocket_manager.is_connected,
        "subscriptions_count": len(websocket_manager.subscriptions),
        "reconnect_attempts": websocket_manager.reconnect_attempts
    } 