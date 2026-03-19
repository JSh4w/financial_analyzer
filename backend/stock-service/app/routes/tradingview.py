"""TradingView UDF datafeed endpoints"""

from datetime import datetime, timezone
from logging import getLogger

from app.auth import get_current_user_id
from app.database.stock_data_manager import StockDataManager
from app.dependencies import get_db_manager
from fastapi import APIRouter, Depends, HTTPException

logger = getLogger(__name__)
router = APIRouter(prefix="/api/tradingview")


@router.get("/config")
async def tradingview_config():
    """TradingView UDF configuration endpoint"""
    return {
        "supports_search": False,
        "supports_group_request": False,
        "supports_marks": False,
        "supports_timescale_marks": False,
        "supports_time": True,
        "supported_resolutions": ["1"],
    }


@router.get("/symbol_info")
async def tradingview_symbol_info(symbol: str):
    """Resolve symbol information for TradingView"""
    return {
        "name": symbol.upper(),
        "ticker": symbol.upper(),
        "description": f"{symbol.upper()} Stock",
        "type": "stock",
        "session": "0930-1600",
        "exchange": "US",
        "listed_exchange": "US",
        "timezone": "America/New_York",
        "minmov": 1,
        "pricescale": 100,
        "has_intraday": True,
        "supported_resolutions": ["1"],
        "volume_precision": 0,
        "data_status": "streaming",
    }


@router.get("/history")
async def tradingview_history(
    symbol: str,
    from_ts: int,
    to_ts: int,
    resolution: str = "1",  # noqa: ARG001 - Reserved for future multi-resolution support
    db_manager: StockDataManager = Depends(get_db_manager),
    _: str = Depends(get_current_user_id),
):
    """Get historical bars for TradingView

    Args:
        symbol: Stock symbol
        from_ts: Unix timestamp (seconds) - start time
        to_ts: Unix timestamp (seconds) - end time
        resolution: Bar resolution (only "1" minute supported now)

    Returns:
        TradingView UDF format:
        {s: "ok", t: [...], o: [...], h: [...], l: [...], c: [...], v: [...]}
    """
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        from_dt = datetime.fromtimestamp(from_ts, tz=timezone.utc)
        to_dt = datetime.fromtimestamp(to_ts, tz=timezone.utc)

        from_timestamp = from_dt.isoformat().replace("+00:00", "Z")
        to_timestamp = to_dt.isoformat().replace("+00:00", "Z")

        candles = db_manager.get_candles_by_time_range(
            symbol.upper(), from_timestamp, to_timestamp
        )

        if not candles:
            return {"s": "no_data", "nextTime": None}

        tv_bars = {
            "s": "ok",
            "t": [],
            "o": [],
            "h": [],
            "l": [],
            "c": [],
            "v": [],
        }

        for timestamp, candle in sorted(candles.items()):
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            tv_bars["t"].append(int(dt.timestamp()))
            tv_bars["o"].append(candle["open"])
            tv_bars["h"].append(candle["high"])
            tv_bars["l"].append(candle["low"])
            tv_bars["c"].append(candle["close"])
            tv_bars["v"].append(candle["volume"])

        logger.info(
            "Returned %s bars for %s from %s to %s",
            len(tv_bars["t"]),
            symbol,
            from_timestamp,
            to_timestamp,
        )
        return tv_bars

    except Exception as e:
        logger.error("TradingView history error for %s: %s", symbol, e)
        raise HTTPException(
            status_code=500, detail=f"Error fetching history: {str(e)}"
        ) from e
