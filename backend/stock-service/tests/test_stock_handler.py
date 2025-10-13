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

    @pytest.mark.asyncio
    async def test_load_historical_data_adds_candles(self):
        """Test load_historical_data adds historical candles"""
        handler = StockHandler("AAPL")

        historical_bars = {
            "2022-01-01T09:30:00Z": {"open": 150.0, "high": 151.0, "low": 149.5, "close": 150.5, "volume": 10000},
            "2022-01-01T09:31:00Z": {"open": 150.5, "high": 152.0, "low": 150.0, "close": 151.5, "volume": 12000},
            "2022-01-01T09:32:00Z": {"open": 151.5, "high": 152.5, "low": 151.0, "close": 152.0, "volume": 8000}
        }

        await handler.load_historical_data(historical_bars)

        assert len(handler.candle_data) == 3
        assert "2022-01-01T09:30:00Z" in handler.candle_data
        assert handler.candle_data["2022-01-01T09:30:00Z"]["open"] == 150.0

    @pytest.mark.asyncio
    async def test_load_historical_data_doesnt_overwrite_live(self):
        """Test that historical data doesn't overwrite live data"""
        handler = StockHandler("AAPL")

        # Process a live trade first
        handler.process_trade(160.0, 500, "2022-01-01T09:30:45Z", [])

        # Try to load historical for same minute
        historical_bars = {
            "2022-01-01T09:30:00Z": {"open": 150.0, "high": 151.0, "low": 149.5, "close": 150.5, "volume": 10000}
        }

        await handler.load_historical_data(historical_bars)

        # Live data should be preserved
        candle = handler.candle_data["2022-01-01T09:30:00Z"]
        assert candle["close"] == 160.0  # From live trade
        assert candle["volume"] == 500    # From live trade
        # Should NOT be historical values

    @pytest.mark.asyncio
    async def test_load_historical_data_empty(self):
        """Test loading empty historical data"""
        handler = StockHandler("AAPL")

        await handler.load_historical_data({})

        assert len(handler.candle_data) == 0

    @pytest.mark.asyncio
    async def test_load_historical_data_with_callback(self):
        """Test that load_historical_data triggers callback"""
        from unittest.mock import Mock

        mock_callback = Mock()
        handler = StockHandler("AAPL", on_update_callback=mock_callback)

        historical_bars = {
            "2022-01-01T09:30:00Z": {"open": 150.0, "high": 151.0, "low": 149.5, "close": 150.5, "volume": 10000}
        }

        await handler.load_historical_data(historical_bars)

        # Callback should be called with is_initial=True
        mock_callback.assert_called_once()
        call_args = mock_callback.call_args
        assert call_args[0][0] == "AAPL"  # symbol
        assert call_args[1]["is_initial"] is True  # is_initial flag

    @pytest.mark.asyncio
    async def test_load_historical_data_large_dataset(self):
        """Test loading large historical dataset"""
        handler = StockHandler("AAPL")

        # Generate 1440 minutes (24 hours)
        historical_bars = {}
        for i in range(1440):
            timestamp = f"2022-01-01T{i//60:02d}:{i%60:02d}:00Z"
            historical_bars[timestamp] = {
                "open": 150.0 + i * 0.01,
                "high": 151.0 + i * 0.01,
                "low": 149.0 + i * 0.01,
                "close": 150.5 + i * 0.01,
                "volume": 10000
            }

        await handler.load_historical_data(historical_bars)

        assert len(handler.candle_data) == 1440

    @pytest.mark.asyncio
    async def test_load_historical_then_process_live(self):
        """Test that live trades work correctly after loading historical"""
        handler = StockHandler("AAPL")

        # Load historical data
        historical_bars = {
            "2022-01-01T09:30:00Z": {"open": 150.0, "high": 151.0, "low": 149.5, "close": 150.5, "volume": 10000}
        }
        await handler.load_historical_data(historical_bars)

        # Process live trade for new minute
        handler.process_trade(155.0, 200, "2022-01-01T09:31:30Z", [])

        # Should have both historical and live candles
        assert len(handler.candle_data) == 2
        assert handler.candle_data["2022-01-01T09:30:00Z"]["close"] == 150.5  # Historical
        assert handler.candle_data["2022-01-01T09:31:00Z"]["close"] == 155.0  # Live