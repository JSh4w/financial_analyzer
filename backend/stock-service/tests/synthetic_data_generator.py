"""Generates synthetic market data for testing and demos"""
import random
import time
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta

from models.websocket_models import TradeData


class SyntheticDataGenerator:
    """Generates realistic synthetic trade data for testing and demos"""
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or [
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX", 
            "ADBE", "CRM", "ORCL", "IBM", "INTC", "AMD", "QCOM", "PYPL",
            "V", "MA", "JPM", "BAC", "WFC", "GS", "MS", "C", "BRK.B",
            "JNJ", "PFE", "UNH", "CVX", "XOM", "KO", "PEP", "WMT", "HD",
            "DIS", "VZ", "T", "CSCO", "BA", "CAT", "MMM", "GE", "F", "GM",
            "UBER", "LYFT", "ZOOM", "SHOP", "SQ", "ROKU"
        ]
        
        # Base prices for realistic data
        self.base_prices = {symbol: random.uniform(50, 400) for symbol in self.symbols}
        
        # Market hours (9:30 AM - 4:00 PM EST in milliseconds)
        self.market_open_hour = 9
        self.market_open_minute = 30
        self.market_close_hour = 16
        self.market_close_minute = 0

    def generate_single_trade(self, symbol: str, timestamp: int = None, 
                            price_volatility: float = 0.02) -> TradeData:
        """Generate a single realistic trade"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        
        base_price = self.base_prices[symbol]
        
        # Add realistic price movement
        price_change = random.gauss(0, base_price * price_volatility)
        price = max(0.01, base_price + price_change)
        
        # Update base price for next trade (price walks)
        self.base_prices[symbol] = price
        
        # Realistic volume (log-normal distribution)
        volume = max(1, int(random.lognormvariate(4, 1.5)))
        
        # Trade conditions (mostly empty, occasional conditions)
        conditions = []
        if random.random() < 0.1:  # 10% chance of conditions
            conditions = random.choice([["I"], ["T"], ["I", "T"], []])
        
        return TradeData(
            s=symbol,
            p=round(price, 2),
            t=timestamp,
            v=volume,
            c=conditions
        )

    def generate_market_day_trades(self, date: datetime, 
                                 trades_per_symbol: int = 100) -> List[TradeData]:
        """Generate a full day of trades for all symbols"""
        trades = []
        
        # Market open timestamp
        market_open = date.replace(
            hour=self.market_open_hour, 
            minute=self.market_open_minute, 
            second=0, 
            microsecond=0
        )
        market_close = date.replace(
            hour=self.market_close_hour, 
            minute=self.market_close_minute, 
            second=0, 
            microsecond=0
        )
        
        # Market duration in milliseconds
        market_duration_ms = int((market_close - market_open).total_seconds() * 1000)
        
        for symbol in self.symbols:
            for i in range(trades_per_symbol):
                # Random time during market hours
                random_offset = random.randint(0, market_duration_ms)
                trade_time = market_open + timedelta(milliseconds=random_offset)
                timestamp = int(trade_time.timestamp() * 1000)
                
                trade = self.generate_single_trade(symbol, timestamp)
                trades.append(trade)
        
        # Sort by timestamp
        trades.sort(key=lambda x: x.t)
        return trades

    def generate_realtime_stream(self, duration_seconds: int = 60, 
                               trades_per_second: int = 10) -> List[TradeData]:
        """Generate a stream of trades for real-time simulation"""
        trades = []
        start_time = int(time.time() * 1000)
        
        for second in range(duration_seconds):
            for _ in range(trades_per_second):
                # Random symbol
                symbol = random.choice(self.symbols)
                
                # Random time within the second
                timestamp = start_time + (second * 1000) + random.randint(0, 999)
                
                trade = self.generate_single_trade(symbol, timestamp)
                trades.append(trade)
        
        return sorted(trades, key=lambda x: x.t)

    def generate_burst_scenario(self, symbol: str, burst_count: int = 50) -> List[TradeData]:
        """Generate a burst of trades for stress testing"""
        trades = []
        base_timestamp = int(time.time() * 1000)
        
        for i in range(burst_count):
            # Trades within a 1-second window
            timestamp = base_timestamp + random.randint(0, 1000)
            trade = self.generate_single_trade(symbol, timestamp, price_volatility=0.05)
            trades.append(trade)
        
        return sorted(trades, key=lambda x: x.t)

    def save_to_file(self, trades: List[TradeData], filename: str):
        """Save trades to JSON file for replay"""
        trade_dicts = [trade.data_to_dict() for trade in trades]
        with open(filename, 'w') as f:
            json.dump(trade_dicts, f, indent=2)

    def load_from_file(self, filename: str) -> List[TradeData]:
        """Load trades from JSON file"""
        with open(filename, 'r') as f:
            trade_dicts = json.load(f)
        return [TradeData.dict_to_data(trade_dict) for trade_dict in trade_dicts]

    def get_sample_symbols(self, count: int = 10) -> List[str]:
        """Get a subset of symbols for smaller tests"""
        return random.sample(self.symbols, min(count, len(self.symbols)))


# Convenience functions for quick testing
def generate_demo_data(symbols_count: int = 10, days: int = 1) -> List[TradeData]:
    """Generate demo data for presentations"""
    generator = SyntheticDataGenerator()
    symbols = generator.get_sample_symbols(symbols_count)
    generator.symbols = symbols
    
    all_trades = []
    base_date = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        date = base_date + timedelta(days=day)
        day_trades = generator.generate_market_day_trades(date, trades_per_symbol=200)
        all_trades.extend(day_trades)
    
    return all_trades


def generate_test_data(symbol: str = "AAPL", count: int = 100) -> List[TradeData]:
    """Generate simple test data for unit tests"""
    generator = SyntheticDataGenerator([symbol])
    trades = []
    base_timestamp = int(time.time() * 1000)
    
    for i in range(count):
        timestamp = base_timestamp + (i * 1000)  # 1 trade per second
        trade = generator.generate_single_trade(symbol, timestamp)
        trades.append(trade)
    
    return trades


if __name__ == "__main__":
    # Example usage - generate demo data
    generator = SyntheticDataGenerator()
    
    # Generate 1 hour of real-time data
    realtime_trades = generator.generate_realtime_stream(duration_seconds=3600)
    generator.save_to_file(realtime_trades, "demo_realtime_trades.json")
    print(f"Generated {len(realtime_trades)} trades for demo")
    
    # Generate full market day
    today = datetime.now()
    daily_trades = generator.generate_market_day_trades(today)
    generator.save_to_file(daily_trades, "demo_daily_trades.json")
    print(f"Generated {len(daily_trades)} daily trades")
    
    # Generate burst test data
    burst_trades = generator.generate_burst_scenario("AAPL", 100)
    generator.save_to_file(burst_trades, "burst_test_trades.json")
    print(f"Generated {len(burst_trades)} burst trades")