"""Processes tick data on a per symbol basis"""
from typing import Dict, Any, Optional, Callable, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class StockHandler():
    """Handles individual stock OHLCV aggregation"""
    def __init__(self, symbol: str, db_manager=None, on_update_callback: Optional[Callable] = None):
        self._symbol = symbol
        self._ohlcv: Dict[str, Dict[str, Any]] = {}  # minute timestamp -> OHLCV data
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

    def process_trade(self, price: float, volume: int, timestamp: str, conditions: Optional[List[str]] = None):
        """Takes current trade and aggregates into minute OHLCV candles
        
        Args:
            price: Trade price
            volume: Trade volume/size
            timestamp: RFC-3339 formatted timestamp (e.g., "2021-02-22T15:51:44.208Z")
            conditions: Optional list of trade conditions
        """
        if any(item in (None, 0) for item in [price, volume]) or not timestamp:
            return

        # Convert RFC-3339 timestamp to minute-aligned timestamp string
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            # Align to minute boundary
            minute_aligned_dt = dt.replace(second=0, microsecond=0)
            minute_timestamp = minute_aligned_dt.isoformat().replace('+00:00', 'Z')
        except (ValueError, AttributeError) as e:
            logger.error("Invalid timestamp format: %s, error: %s", timestamp, e)
            return

        # Update existing candle
        candle = self._ohlcv.setdefault(minute_timestamp, {
            'high': price, 'low': price, 'open': price,
            'close': price, 'volume': 0,
        })
        
        candle['high'] = max(candle['high'], price)
        candle['low'] = min(candle['low'], price)
        candle['volume'] += volume
        candle['close'] = price
        
        # Persist to DuckDB immediately
        if self.db_manager:
            # Insert individual trade record
            self.db_manager.insert_trade(self._symbol, price, volume, timestamp, conditions or [])
            # Update OHLCV candle
            self.db_manager.upsert_candle(self._symbol, minute_timestamp, candle)
        
        # Trigger update callback if set
        if self.on_update_callback:
            self.on_update_callback(self._symbol, self._ohlcv)

    def save_to_database(self):
        """Bulk save all in-memory data to database"""
        if self.db_manager and self._ohlcv:
            self.db_manager.bulk_upsert_candles(self._symbol, self._ohlcv)
            logger.info(f"Bulk saved {len(self._ohlcv)} candles for {self._symbol}")

    @property
    def symbol(self):
        """Stock symbol"""
        return self._symbol

    @property
    def candle_data(self):
        """OHLCV data"""
        return self._ohlcv