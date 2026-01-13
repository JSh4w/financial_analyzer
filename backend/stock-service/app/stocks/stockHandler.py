"""Processes tick data on a per symbol basis"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .OHLCV_buffer import OHLCVBuffer

logger = logging.getLogger(__name__)


class StockHandler:
    """Handles individual stock OHLCV aggregation"""

    def __init__(
        self,
        symbol: str,
        db_manager=None,
        on_update_callback: Optional[Callable] = None,
        buffer_maxlen: int = 10_000,
    ):
        self._symbol = symbol
        self._ohlcv = OHLCVBuffer(maxlen=buffer_maxlen)
        self.db_manager = db_manager
        self.on_update_callback = on_update_callback

        # Load recent data from database on initialization
        logger.info(f"Initializing StockHandler for {symbol}")
        if self.db_manager:
            self._load_recent_data()

    def _load_recent_data(self, hours: int = 24):
        """Load recent candles from database into memory - use just for initialisation"""
        if self.db_manager:
            recent_candles = self.db_manager.get_recent_candles(
                self._symbol, limit=hours * 60
            )
            # Bulk load into buffer
            self._ohlcv.bulk_update(recent_candles)
            logger.info(
                f"Loaded {len(recent_candles)} recent candles for {self._symbol}"
            )

    def process_trade(
        self,
        price: float,
        volume: int,
        timestamp: str,
        conditions: Optional[List[str]] = None,
    ):
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
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            # Align to minute boundary
            minute_aligned_dt = dt.replace(second=0, microsecond=0)
            minute_timestamp = minute_aligned_dt.isoformat().replace("+00:00", "Z")
        except (ValueError, AttributeError) as e:
            logger.error("Invalid timestamp format: %s, error: %s", timestamp, e)
            return

        # Add or update candle in buffer
        is_new_candle = self._ohlcv.add_or_update_candle(
            minute_timestamp, price, volume
        )

        # Use shared helper for final processing
        self._update_candle_data(minute_timestamp, is_new_candle)

    def process_candle(self, candle_data: Dict[str, Any]):
        """Process complete candle data directly (for minute bar subscriptions)

        Args:
            candle_data: Dict containing 'open', 'high', 'low', 'close', 'volume', 'timestamp'
        """
        try:
            timestamp = candle_data["timestamp"]

            # Convert RFC-3339 timestamp to minute-aligned timestamp string
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            minute_aligned_dt = dt.replace(second=0, microsecond=0)
            minute_timestamp = minute_aligned_dt.isoformat().replace("+00:00", "Z")

            # Store the complete candle directly in buffer
            self._ohlcv.set_candle(minute_timestamp, candle_data)

            # Use shared helper for final processing (always save complete candles immediately)
            self._update_candle_data(minute_timestamp, save_immediately=True)

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Failed to process candle data for %s: %s", self._symbol, e)

    def _update_candle_data(
        self,
        minute_timestamp: str,
        is_new_candle: bool = False,
        save_immediately: bool = False,
    ):
        """Shared helper for database operations and callbacks"""

        # Save to database logic
        if self.db_manager:
            if save_immediately:
                # Save current candle immediately (for complete candle data)
                self.db_manager.upsert_candle(
                    self._symbol, minute_timestamp, self._ohlcv[minute_timestamp]
                )
                logger.debug(f"Saved candle for {self._symbol} at {minute_timestamp}")
            elif is_new_candle and len(self._ohlcv) > 1:
                # Save previous completed candle (for incremental trade data)
                # With SortedDict, no need to sort - keys are already ordered
                latest_candles = self._ohlcv.get_latest(2)
                timestamps = list(latest_candles.keys())
                if len(timestamps) >= 2:
                    prev_timestamp = timestamps[0]  # First of the 2 (older one)
                    prev_candle = latest_candles[prev_timestamp]
                    self.db_manager.upsert_candle(
                        self._symbol, prev_timestamp, prev_candle
                    )
                    logger.debug(
                        f"Saved completed candle for {self._symbol} at {prev_timestamp}"
                    )

        # Trigger update callback if set - send only the updated candle(s)
        if self.on_update_callback:
            # Send only the most recent 2 candles (current + previous if new)
            delta_candles = self._ohlcv.get_latest(2)
            self.on_update_callback(self._symbol, delta_candles, is_initial=False)

    def save_to_database(self):
        """Bulk save all in-memory data to database"""
        if self.db_manager and len(self._ohlcv) > 0:
            all_candles = self._ohlcv.get_all()
            self.db_manager.bulk_upsert_candles(self._symbol, all_candles)
            logger.info(f"Bulk saved {len(self._ohlcv)} candles for {self._symbol}")

    @property
    def symbol(self):
        """Stock symbol"""
        return self._symbol

    @property
    def candle_data(self):
        """OHLCV data - returns dict for backward compatibility"""
        return self._ohlcv.get_all()

    async def load_historical_data(self, historical_bars: Dict[str, Dict[str, Any]]):
        """
        Load historical bar data into the handler
        No lock needed - asyncio cooperative concurrency ensures atomic dict operations

        Args:
            historical_bars: Dictionary of timestamp -> OHLCV data
        """
        # Bulk update buffer
        initial_count = len(self._ohlcv)
        self._ohlcv.bulk_update(historical_bars)
        new_count = len(self._ohlcv) - initial_count

        logger.info(f"Loaded {new_count} new historical bars for {self._symbol}")

        # Optionally save to database IN BACKGROUND (don't block async code)
        if self.db_manager and new_count > 0:
            # Get only the new bars that were added
            new_bars = {
                ts: bar for ts, bar in historical_bars.items() if ts in self._ohlcv
            }
            # Run synchronous DB operation in thread pool to avoid blocking
            await asyncio.to_thread(
                self.db_manager.bulk_upsert_candles, self._symbol, new_bars
            )

        # Trigger callback to notify frontend of initial data (send all candles)
        if self.on_update_callback:
            all_candles = self._ohlcv.get_all()
            self.on_update_callback(self._symbol, all_candles, is_initial=True)
