"""Historical data fetcher for Alpaca API"""
import httpx
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from models.websocket_models import BarData

logger = logging.getLogger(__name__)


class AlpacaHistoricalData:
    """Fetches historical bar data from Alpaca REST API"""

    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://data.alpaca.markets"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret
        }

    async def fetch_historical_bars(
        self,
        symbol: str,
        timeframe: str = "1Min",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[BarData]:
        """
        Fetch historical bar data from Alpaca

        Args:
            symbol: Stock symbol
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
            start: Start datetime (defaults to 7 days ago to ensure we get trading days)
            end: End datetime (defaults to now)
            limit: Maximum number of bars to fetch (max 10000)

        Returns:
            List of BarData instances
        """
        if start is None:
            # Go back 7 days to ensure we capture at least one trading week
            # This handles weekends and holidays
            start = datetime.now(timezone.utc) - timedelta(days=7)
        if end is None:
            end = datetime.now(timezone.utc)

        # Format timestamps for Alpaca API (RFC-3339)
        start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

        url = f"{self.base_url}/v2/stocks/{symbol}/bars"
        params = {
            "timeframe": timeframe,
            "start": start_str,
            "end": end_str,
            "limit": limit,
            "adjustment": "raw",  # No adjustments for splits/dividends
            "feed": "iex"  # Use IEX feed
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                # Convert to BarData instances
                return self._parse_bars_response(data, symbol)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching historical data for {symbol}: {e.response.status_code} - {e.response.text}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Request error fetching historical data for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching historical data for {symbol}: {e}")
            return []

    def _parse_bars_response(self, data: dict, symbol: str) -> List[BarData]:
        """
        Parse Alpaca bars API response into BarData instances

        Expected format:
        {
            "bars": [
                {
                    "t": "2021-02-01T16:01:00Z",
                    "o": 133.32,
                    "h": 133.74,
                    "l": 133.31,
                    "c": 133.5,
                    "v": 9876,
                    "n": 123,
                    "vw": 133.45
                }
            ],
            "symbol": "AAPL",
            "next_page_token": null
        }

        Returns:
            List of BarData instances
        """
        bars = data.get("bars")

        # Handle case where Alpaca returns null instead of empty array
        if bars is None:
            logger.warning(f"No bars data returned for {symbol} (API returned null)")
            return []

        result = []

        for bar in bars:
            try:
                bar_data = BarData(
                    T='b',
                    S=symbol,
                    o=bar["o"],
                    h=bar["h"],
                    l=bar["l"],
                    c=bar["c"],
                    v=bar["v"],
                    t=bar["t"],
                    n=bar.get("n", 0),
                    vw=bar.get("vw", 0.0)
                )
                result.append(bar_data)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse bar: {bar}, error: {e}")
                continue

        logger.info(f"Parsed {len(result)} historical bars for {symbol}")
        return result
