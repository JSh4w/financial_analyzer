"""Unit tests for StockHandler class"""
import pytest
from datetime import datetime, timezone
from models.websocket_models import TradeData
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
        trade = TradeData(
            s="AAPL",
            p=150.0,
            t=1640995200000,  # 2022-01-01 00:00:00 UTC
            v=100,
            c=[]
        )

        handler.process_trade(trade)

        # Should have current candle
        last_trade = list(handler.candle_data.values())[-1]
        assert last_trade is not None
        assert last_trade['open'] == 150.0
        assert last_trade['high'] == 150.0
        assert last_trade['low'] == 150.0
        assert last_trade['close'] == 150.0
        assert last_trade['volume'] == 100

    def test_multiple_trades_same_day(self):
        """Test multiple trades in same day update OHLCV correctly"""
        handler = StockHandler("AAPL")
        base_timestamp = 1640995200000  # 2022-01-01 00:00:00 UTC

        trades = [
            TradeData(s="AAPL", p=150.0, t=base_timestamp + 1000, v=100, c=[]),
            TradeData(s="AAPL", p=155.0, t=base_timestamp + 2000, v=50, c=[]),
            TradeData(s="AAPL", p=148.0, t=base_timestamp + 3000, v=75, c=[]),
            TradeData(s="AAPL", p=152.0, t=base_timestamp + 4000, v=25, c=[])
        ]

        for trade in trades:
            handler.process_trade(trade)

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
        invalid_trade1 = TradeData(s="AAPL", p=None, t=1640995200000, v=100, c=[])
        handler.process_trade(invalid_trade1)
        assert not handler.candle_data, handler.candle_data

        # Trade with missing timestamp
        invalid_trade2 = TradeData(s="AAPL", p=150.0, t=None, v=100, c=[])
        handler.process_trade(invalid_trade2)
        assert not handler.candle_data, handler.candle_data

    def test_zero_volume_handling(self):
        """Test handling of zero volume trades"""
        handler = StockHandler("AAPL")
        trade = TradeData(s="AAPL", p=150.0, t=1640995200000, v=0, c=[])
        handler.process_trade(trade)

        assert not handler.candle_data, handler.candle_data

    def test_trade_conditions_preserved(self):
        """Test that trade conditions are accessible (even if not used)"""
        handler = StockHandler("AAPL")
        trade = TradeData(s="AAPL", p=150.0, t=1640995200000, v=100, c=["I", "T"])

        # Verify the trade data structure is correct
        assert trade.c == ["I", "T"]

        # Process trade (conditions not used in OHLCV but available)
        handler.process_trade(trade)
        assert handler.candle_data is not None

    @pytest.fixture
    def sample_trades(self):
        """Fixture providing sample trade data"""
        base_timestamp = 1640995200000
        return [
            TradeData(s="AAPL", p=150.0, t=base_timestamp + i * 1000, v=100, c=[])
            for i in range(10)
        ]

    def test_performance_many_trades(self, sample_trades):
        """Test performance with many trades"""
        handler = StockHandler("AAPL")

        # Process all trades
        for trade in sample_trades:
            handler.process_trade(trade)

        # Should have one candle with accumulated data
        assert handler.candle_data is not None
        assert list(handler.candle_data.values())[-1]['volume'] == 1000  # 100 * 10 trades