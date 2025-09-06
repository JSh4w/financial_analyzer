"""Unit tests for StockHandler class"""
import pytest
from app.stocks.stockHandler import StockHandler


class TestStockHandler:
    """Unit tests for StockHandler functionality"""

    def test_stock_handler_initialization(self):
        """Test StockHandler creates correctly"""
        handler = StockHandler("AAPL")
        assert handler.symbol == "AAPL"
        assert handler._ohlcv == {}

    def test_single_trade_processing(self):
        """Test processing a single trade creates initial candle"""
        handler = StockHandler("AAPL")
        
        handler.process_trade(
            price=150.0,
            volume=100,
            timestamp="2022-01-01T00:00:00Z",
            conditions=[]
        )

        # Should have current candle
        last_trade = list(handler.candle_data.values())[-1]
        assert last_trade is not None
        assert last_trade['open'] == 150.0
        assert last_trade['high'] == 150.0
        assert last_trade['low'] == 150.0
        assert last_trade['close'] == 150.0
        assert last_trade['volume'] == 100

    def test_multiple_trades_same_minute(self):
        """Test multiple trades in same minute update OHLCV correctly"""
        handler = StockHandler("AAPL")

        trades = [
            (150.0, 100, "2022-01-01T00:00:10Z", []),
            (155.0, 50, "2022-01-01T00:00:20Z", []),
            (148.0, 75, "2022-01-01T00:00:30Z", []),
            (152.0, 25, "2022-01-01T00:00:40Z", [])
        ]

        for price, volume, timestamp, conditions in trades:
            handler.process_trade(
                price=price,
                volume=volume,
                timestamp=timestamp,
                conditions=conditions
            )

        candle = list(handler.candle_data.values())[-1]
        assert candle['open'] == 150.0  # First trade
        assert candle['high'] == 155.0  # Highest price
        assert candle['low'] == 148.0   # Lowest price
        assert candle['close'] == 152.0 # Last trade
        assert candle['volume'] == 250  # Sum of volumes

    def test_invalid_trade_data_handling(self):
        """Test handling of invalid trade data"""
        handler = StockHandler("AAPL")

        # Trade with missing price
        handler.process_trade(
            price=None,
            volume=100,
            timestamp="2022-01-01T00:00:00Z",
            conditions=[]
        )
        assert not handler.candle_data

        # Trade with missing timestamp
        handler.process_trade(
            price=150.0,
            volume=100,
            timestamp=None,
            conditions=[]
        )
        assert not handler.candle_data

    def test_zero_volume_handling(self):
        """Test handling of zero volume trades"""
        handler = StockHandler("AAPL")
        handler.process_trade(
            price=150.0,
            volume=0,
            timestamp="2022-01-01T00:00:00Z",
            conditions=[]
        )
        assert not handler.candle_data

    def test_trade_conditions_preserved(self):
        """Test that trade conditions are passed correctly"""
        handler = StockHandler("AAPL")
        
        handler.process_trade(
            price=150.0,
            volume=100,
            timestamp="2022-01-01T00:00:00Z",
            conditions=["I", "T"]
        )
        assert handler.candle_data is not None

    def test_performance_many_trades(self):
        """Test performance with many trades"""
        handler = StockHandler("AAPL")

        # Process trades in the same minute
        for i in range(10):
            handler.process_trade(
                price=150.0,
                volume=100,
                timestamp=f"2022-01-01T00:00:{i:02d}Z",
                conditions=[]
            )

        # Should have one candle with accumulated data
        assert handler.candle_data is not None
        assert list(handler.candle_data.values())[-1]['volume'] == 1000  # 100 * 10 trades

    def test_timestamp_minute_alignment(self):
        """Test that trades are aligned to minute boundaries"""
        handler = StockHandler("AAPL")
        
        # Trades at different seconds within the same minute
        handler.process_trade(150.0, 100, "2022-01-01T12:34:15Z", [])
        handler.process_trade(155.0, 50, "2022-01-01T12:34:45Z", [])
        
        # Should have one candle aligned to minute
        assert len(handler.candle_data) == 1
        timestamp = list(handler.candle_data.keys())[0]
        assert timestamp == "2022-01-01T12:34:00Z"