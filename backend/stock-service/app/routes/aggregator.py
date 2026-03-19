from app.auth import get_current_user_id
from app.dependencies import get_data_aggregator
from app.stocks.data_aggregator import TradeDataAggregator
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/aggregator")


# Data Aggregator Endpoints
@router.get("/aggregator/status")
async def get_aggregator_status(
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    _: str = Depends(get_current_user_id),
):
    """Get status of the data aggregator"""
    if data_aggregator is None:
        return {"status": "stopped", "message": "Data aggregator is not running"}

    return {
        "status": "running",
        "symbols_tracked": data_aggregator.get_all_symbols(),
        "queue_size": data_aggregator.queue.qsize(),
    }


@router.get("/aggregator/symbols")
async def get_tracked_symbols(
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    _: str = Depends(get_current_user_id),
):
    """Get all symbols being tracked by the aggregator"""
    if data_aggregator is None:
        return {"error": "Data aggregator is not running"}

    return {"symbols": data_aggregator.get_all_symbols()}


@router.get("/aggregator/data/{symbol}")
async def get_symbol_data(
    symbol: str,
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    _: str = Depends(get_current_user_id),
):
    """Get OHLCV data for a specific symbol"""
    if data_aggregator is None:
        return {"error": "Data aggregator is not running"}

    stock_handler = data_aggregator.get_stock_handler(symbol.upper())
    if stock_handler is None:
        return {"error": f"No data found for symbol {symbol}"}

    return {"symbol": symbol.upper(), "candle_data": stock_handler.candle_data}


@router.get("/aggregator/data")
async def get_all_aggregated_data(
    data_aggregator: TradeDataAggregator = Depends(get_data_aggregator),
    _: str = Depends(get_current_user_id),
):
    """Get OHLCV data for all tracked symbols"""
    if data_aggregator is None:
        return {"error": "Data aggregator is not running"}

    all_data = {}
    for symbol in data_aggregator.get_all_symbols():
        stock_handler = data_aggregator.get_stock_handler(symbol)
        if stock_handler:
            all_data[symbol] = stock_handler.candle_data

    return {"data": all_data}
