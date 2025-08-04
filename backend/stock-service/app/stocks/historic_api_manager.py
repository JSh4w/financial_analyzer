"""Historic API Manager for Alpha Vantage integration"""
import logging
from typing import Optional, Dict
import requests
from app.config import Settings
from models.stock_models import DailyStockData, IntradayStockData, IntradayMetaData, DailyMetaData

logger = logging.getLogger(__name__)
settings = Settings()

class HistoricApiManager:
    """Manager for fetching historic stock data from Alpha Vantage API"""

    def __init__(self):
        self.api_key = settings.ALPHA_VANTAGE_API_KEY
        self.base_url = "https://www.alphavantage.co/query"
        self.session = requests.Session()
    def get_daily_stock_data(
        self, symbol: str, outputsize: str = "compact"
    ) -> Optional[Dict[str, list[DailyStockData] | DailyMetaData]]:
        """
        Fetch daily stock data from Alpha Vantage

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            outputsize: 'compact' (last 100 days) or 'full' (20+ years)

        Returns:
            Dict with 'metadata' and 'data' keys containing structured objects
        """
        try:
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol,
                'outputsize': outputsize,
                'apikey': self.api_key
            }

            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()

            if "Error Message" in data:
                logger.error("Alpha Vantage API error: %s", data["Error Message"])
                return None

            if "Note" in data:
                logger.warning("Alpha Vantage API limit: %s", data["Note"])
                return None

            # Parse metadata
            meta_raw = data.get("Meta Data", {})
            metadata = DailyMetaData(
                information=meta_raw.get("1. Information", ""),
                symbol=meta_raw.get("2. Symbol", ""),
                last_refreshed=meta_raw.get("3. Last Refreshed", ""),
                output_size=meta_raw.get("4. Output Size", ""),
                time_zone=meta_raw.get("5. Time Zone", "")
            )

            time_series = data.get("Time Series (Daily)", {})

            stock_data_list = []
            for date_str, daily_data in time_series.items():
                stock_data = DailyStockData(
                    symbol=symbol,
                    date=date_str,
                    open_price=float(daily_data["1. open"]),
                    high=float(daily_data["2. high"]),
                    low=float(daily_data["3. low"]),
                    close=float(daily_data["4. close"]),
                    volume=int(daily_data["5. volume"])
                )
                stock_data_list.append(stock_data)

            logger.info("Fetched %d days of data for %s", len(stock_data_list), symbol)
            return {"metadata": metadata, "data": stock_data_list}
        except requests.RequestException as e:
            logger.error("Network error fetching data for %s: %s", symbol, e)
            return None
        except (KeyError, ValueError) as e:
            logger.error("Data parsing error for %s: %s", symbol, e)
            return None

    def get_intraday_stock_data(
        self, symbol: str, interval: str = "5min"
    ) -> Optional[Dict[str, list[IntradayStockData] | IntradayMetaData]]:
        """
        Fetch intraday stock data from Alpha Vantage

        Args:
            symbol: Stock symbol
            interval: Time interval ('1min', '5min', '15min', '30min', '60min')

        Returns:
            Dict with 'metadata' and 'data' keys containing structured objects
        """
        try:
            params = {
                'function': 'TIME_SERIES_INTRADAY',
                'symbol': symbol,
                'interval': interval,
                'apikey': self.api_key
            }

            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()

            if "Error Message" in data:
                logger.error("Alpha Vantage API error: %s", data["Error Message"])
                return None

            if "Note" in data:
                logger.warning("Alpha Vantage API limit: %s", data["Note"])
                return None

            # Parse metadata
            meta_raw = data.get("Meta Data", {})
            metadata = IntradayMetaData(
                information=meta_raw.get("1. Information", ""),
                symbol=meta_raw.get("2. Symbol", ""),
                last_refreshed=meta_raw.get("3. Last Refreshed", ""),
                interval=meta_raw.get("4. Interval", ""),
                output_size=meta_raw.get("5. Output Size", ""),
                time_zone=meta_raw.get("6. Time Zone", "")
            )

            # Parse time series data
            time_series_key = f"Time Series ({interval})"
            time_series = data.get(time_series_key, {})

            intraday_data = []
            for timestamp, price_data in time_series.items():
                intraday_point = IntradayStockData(
                    symbol=symbol,
                    timestamp=timestamp,
                    interval=interval,
                    open_price=float(price_data["1. open"]),
                    high=float(price_data["2. high"]),
                    low=float(price_data["3. low"]),
                    close=float(price_data["4. close"]),
                    volume=int(price_data["5. volume"])
                )
                intraday_data.append(intraday_point)

            logger.info("Fetched %d intraday points for %s", len(intraday_data), symbol)
            return {"metadata": metadata, "data": intraday_data}
        except requests.RequestException as e:
            logger.error("Network error fetching intraday data for %s: %s", symbol, e)
            return None
        except (KeyError, ValueError) as e:
            logger.error("Data parsing error for intraday %s: %s", symbol, e)
            return None
