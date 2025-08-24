"""Processes tick data on a per symbol basis"""
from typing import Dict, Any, Optional

from models.websocket_models import TradeData


class StockHandler():
    """Handles individual stock"""
    def __init__(self, symbol: str, db=None):
        self._symbol = symbol
        self._ohlcv: Dict[int, Dict[str, Any]] = {}  # daily timestamp -> OHLCV data
        self.db = db

    def process_trade(self, trade_data: TradeData):
        """Takes current trade and aggregates over daily intervals aligned with UTC
        For smaller storage data is accepted in any order and open and close only reflect
        the """
        # Extract trade data from TradeData dataclass
        price = trade_data.p
        volume = trade_data.v
        timestamp = trade_data.t
        if any(item in (None, 0) for item in [price,volume,timestamp]):
            return

        minute_stamp = timestamp - (timestamp % 60000)
        # Update existing candle or create new one
        if minute_stamp not in self._ohlcv:
            # First trade for this minute - initialize all fields
            self._ohlcv[minute_stamp] = {
                'high': price,
                'low': price,
                'open': price,
                'close': price,
                'volume': volume
            }
        else:
            # Update existing candle
            candle = self._ohlcv[minute_stamp]
            candle['high'] = max(candle['high'], price)
            candle['low'] = min(candle['low'], price)
            candle['volume'] += volume
            candle['close'] = price

    def update_duckdb(self, trade_data: TradeData):
        """Place holder for data persistancy"""
        return trade_data

    @property
    def symbol(self):
        "stock symbol"
        return self._symbol

    @property
    def candle_data(self):
        "OHLCV data"
        return self._ohlcv
    
    @property
    def _current_candle(self):
        "Current candle data (for testing compatibility)"
        if self._ohlcv:
            # Return the most recent candle
            latest_timestamp = max(self._ohlcv.keys())
            return self._ohlcv[latest_timestamp]
        return None