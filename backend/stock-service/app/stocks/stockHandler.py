"""Processes tick data on a per symbol basis"""
from typing import Dict, Any, Optional, Callable
import logging

from models.websocket_models import TradeData

logger = logging.getLogger(__name__)


class StockHandler():
    """Handles individual stock"""
    def __init__(self, symbol: str, db_manager=None, on_update_callback: Optional[Callable] = None):
        self._symbol = symbol
        self._ohlcv: Dict[int, Dict[str, Any]] = {}  # minute timestamp -> OHLCV data
        self.db_manager = db_manager
        self.on_update_callback = on_update_callback
        
        # Load recent data from database on initialization
        if self.db_manager:
            self._load_recent_data()

    def _load_recent_data(self, hours: int = 24):
        """Load recent candles from database into memory - use just for initialisation"""
        if self.db_manager:
            recent_candles = self.db_manager.get_recent_candles(self._symbol, limit=hours*60)
            # only update _ohlcv with old data, only adding data so race conditions should be fine
            self._ohlcv.update({k: v for k, v in recent_candles.items() if k not in self._ohlcv})
            logger.info(f"Loaded {len(recent_candles)} recent candles for {self._symbol}")

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

        # TODO : change ohlcv for open and close to also store timestamp for open and closing

        minute_stamp = timestamp - (timestamp % 60000)
        # Update existing candle
        candle = self._ohlcv.setdefault(minute_stamp, {
            'high':price, 'low':price, 'open':price,
            'close':price, 'volume':0,
            }) # reference to dictionary
        candle['high'] = max(candle['high'], price)
        candle['low'] = min(candle['low'], price)
        candle['volume'] += volume
        candle['close'] = price
        
        # Persist to DuckDB immediately
        if self.db_manager:
            # Insert individual trade record
            self.db_manager.insert_trade(self._symbol, price, volume, timestamp, trade_data.c)
            # Update OHLCV candle
            self.db_manager.upsert_candle(self._symbol, minute_stamp, candle)
        
        # Trigger update callback if set
        if self.on_update_callback:
            self.on_update_callback(self._symbol, self._ohlcv)

    def save_to_database(self):
        """Bulk save all in-memory data to database"""
        if self.db_manager and self._ohlcv:
            self.db_manager.bulk_upsert_candles(self._symbol, self._ohlcv)
            logger.info(f"Bulk saved {len(self._ohlcv)} candles for {self._symbol}")

    def update_duckdb(self, trade_data: TradeData):
        """Place holder for data persistancy (deprecated - use save_to_database)"""
        return trade_data

    @property
    def symbol(self):
        "stock symbol"
        return self._symbol

    @property
    def candle_data(self):
        "OHLCV data"
        return self._ohlcv