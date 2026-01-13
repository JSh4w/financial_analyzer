"""Storage of tick data aggregated into minute OHLCV candles"""
from typing import Dict, Any, Optional
from sortedcontainers import SortedDict
import logging

logger = logging.getLogger(__name__)


class OHLCVBuffer:
    """Buffer to store OHLCV candles with a maximum length"""

    def __init__(self, maxlen: int = 10_000):
        """
        Initialize OHLCV buffer with sorted timestamp keys

        Args:
            maxlen: Maximum number of candles to store (oldest are removed)
        """
        self.data: SortedDict[str, Dict[str, Any]] = SortedDict()
        self.maxlen = maxlen

    def add_or_update_candle(
        self,
        timestamp: str,
        price: float,
        volume: int,
    ) -> bool:
        """
        Add or update a candle with trade data

        Args:
            timestamp: ISO 8601 timestamp (minute-aligned)
            price: Trade price
            volume: Trade volume

        Returns:
            True if this created a new candle, False if updated existing
        """
        is_new = timestamp not in self.data

        candle = self.data.setdefault(
            timestamp,
            {
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 0,
            },
        )

        candle["high"] = max(candle["high"], price)
        candle["low"] = min(candle["low"], price)
        candle["volume"] += volume
        candle["close"] = price

        # Enforce maxlen - remove oldest candles
        while len(self.data) > self.maxlen:
            self.data.popitem(index=0)

        return is_new

    def set_candle(self, timestamp: str, candle_data: Dict[str, Any]) -> None:
        """
        Set complete candle data directly

        Args:
            timestamp: ISO 8601 timestamp
            candle_data: Dict with 'open', 'high', 'low', 'close', 'volume'
        """
        self.data[timestamp] = {
            "open": candle_data["open"],
            "high": candle_data["high"],
            "low": candle_data["low"],
            "close": candle_data["close"],
            "volume": candle_data["volume"],
        }

        # Enforce maxlen
        while len(self.data) > self.maxlen:
            self.data.popitem(index=0)

    def bulk_update(self, candles: Dict[str, Dict[str, Any]]) -> None:
        """
        Bulk update with multiple candles

        Args:
            candles: Dict of timestamp -> OHLCV data
        """
        # Filter out existing timestamps to avoid overwriting newer data
        new_candles = {
            ts: candle for ts, candle in candles.items() if ts not in self.data
        }
        self.data.update(new_candles)

        # Enforce maxlen - remove oldest candles
        while len(self.data) > self.maxlen:
            self.data.popitem(index=0)

    def get_latest(self, n: int = 1) -> Dict[str, Dict[str, Any]]:
        """
        Get the N most recent candles

        Args:
            n: Number of candles to retrieve

        Returns:
            Dict of timestamp -> OHLCV data
        """
        if not self.data:
            return {}
        return dict(self.data.items()[-n:])

    def get_range(
        self, start: Optional[str] = None, end: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get candles within a time range

        Args:
            start: Start timestamp (inclusive), None for beginning
            end: End timestamp (inclusive), None for end

        Returns:
            Dict of timestamp -> OHLCV data
        """
        if start is None and end is None:
            return dict(self.data)

        return dict(self.data.irange(minimum=start, maximum=end, inclusive=(True, True)))

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all candles as a dict"""
        return dict(self.data)

    def __len__(self) -> int:
        """Return number of candles stored"""
        return len(self.data)

    def __contains__(self, timestamp: str) -> bool:
        """Check if timestamp exists"""
        return timestamp in self.data

    def __getitem__(self, timestamp: str) -> Dict[str, Any]:
        """Get candle by timestamp"""
        return self.data[timestamp]
