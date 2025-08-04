"""Stock models for historic information"""
from pydantic import BaseModel

class DailyMetaData(BaseModel):
    """Metadata for daily stock data"""
    information: str
    symbol: str
    last_refreshed: str
    output_size: str
    time_zone: str

class DailyStockData(BaseModel):
    """Stock data for daily start and end values"""
    symbol: str
    date: str
    open_price: float
    high: float
    low: float
    close: float
    volume: int

class IntradayMetaData(BaseModel):
    """Metadata for intraday stock data"""
    information: str
    symbol: str
    last_refreshed: str
    interval: str
    output_size: str
    time_zone: str

class IntradayStockData(BaseModel):
    """Stock data for intraday intervals"""
    symbol: str
    timestamp: str
    interval: str
    open_price: float
    high: float
    low: float
    close: float
    volume: int

# https://www.alphavantage.co/documentation/
# Use the above link to get stock_schema 