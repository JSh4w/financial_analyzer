"""Tests for AlpacaHistoricalData - fetching historical bars from Alpaca REST API"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone, timedelta
from models.websocket_models import BarData
from app.stocks.historical_data import AlpacaHistoricalData


class TestAlpacaHistoricalData:
    """Test suite for AlpacaHistoricalData"""

    @pytest.fixture
    def historical_fetcher(self):
        """Create AlpacaHistoricalData instance with test credentials"""
        return AlpacaHistoricalData(
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

    @pytest.fixture
    def sample_alpaca_response(self):
        """Sample Alpaca API response"""
        return {
            "bars": [
                {
                    "t": "2022-01-01T09:30:00Z",
                    "o": 150.0,
                    "h": 151.0,
                    "l": 149.5,
                    "c": 150.5,
                    "v": 10000,
                    "n": 50,
                    "vw": 150.25
                },
                {
                    "t": "2022-01-01T09:31:00Z",
                    "o": 150.5,
                    "h": 152.0,
                    "l": 150.0,
                    "c": 151.5,
                    "v": 12000,
                    "n": 60,
                    "vw": 151.0
                },
                {
                    "t": "2022-01-01T09:32:00Z",
                    "o": 151.5,
                    "h": 152.5,
                    "l": 151.0,
                    "c": 152.0,
                    "v": 8000,
                    "n": 40,
                    "vw": 151.75
                }
            ],
            "symbol": "AAPL",
            "next_page_token": None
        }

    def test_initialization(self, historical_fetcher):
        """Test AlpacaHistoricalData initializes correctly"""
        assert historical_fetcher.api_key == "test_api_key"
        assert historical_fetcher.api_secret == "test_api_secret"
        assert historical_fetcher.base_url == "https://data.alpaca.markets"
        assert "APCA-API-KEY-ID" in historical_fetcher.headers
        assert "APCA-API-SECRET-KEY" in historical_fetcher.headers

    def test_initialization_custom_base_url(self):
        """Test initialization with custom base URL"""
        fetcher = AlpacaHistoricalData(
            api_key="key",
            api_secret="secret",
            base_url="https://custom.alpaca.markets"
        )
        assert fetcher.base_url == "https://custom.alpaca.markets"

    def test_parse_bars_response_returns_list_of_bardata(self, historical_fetcher, sample_alpaca_response):
        """Test _parse_bars_response returns List[BarData]"""
        result = historical_fetcher._parse_bars_response(sample_alpaca_response, "AAPL")

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(bar, BarData) for bar in result)

    def test_parse_bars_response_bardata_fields(self, historical_fetcher, sample_alpaca_response):
        """Test that BarData instances have correct fields"""
        result = historical_fetcher._parse_bars_response(sample_alpaca_response, "AAPL")

        first_bar = result[0]
        assert first_bar.T == 'b'
        assert first_bar.S == "AAPL"
        assert first_bar.o == 150.0
        assert first_bar.h == 151.0
        assert first_bar.l == 149.5
        assert first_bar.c == 150.5
        assert first_bar.v == 10000
        assert first_bar.t == "2022-01-01T09:30:00Z"
        assert first_bar.n == 50
        assert first_bar.vw == 150.25

    def test_parse_bars_response_empty_bars(self, historical_fetcher):
        """Test parsing response with no bars"""
        empty_response = {"bars": [], "symbol": "AAPL", "next_page_token": None}

        result = historical_fetcher._parse_bars_response(empty_response, "AAPL")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_parse_bars_response_missing_fields(self, historical_fetcher):
        """Test parsing bars with missing optional fields"""
        response = {
            "bars": [
                {
                    "t": "2022-01-01T09:30:00Z",
                    "o": 150.0,
                    "h": 151.0,
                    "l": 149.5,
                    "c": 150.5,
                    "v": 10000
                    # Missing 'n' and 'vw'
                }
            ],
            "symbol": "AAPL"
        }

        result = historical_fetcher._parse_bars_response(response, "AAPL")

        assert len(result) == 1
        assert result[0].n == 0  # Default value
        assert result[0].vw == 0.0  # Default value

    def test_parse_bars_response_invalid_bar_skipped(self, historical_fetcher):
        """Test that invalid bars are skipped"""
        response = {
            "bars": [
                {  # Valid bar
                    "t": "2022-01-01T09:30:00Z",
                    "o": 150.0,
                    "h": 151.0,
                    "l": 149.5,
                    "c": 150.5,
                    "v": 10000
                },
                {  # Invalid bar (missing required field)
                    "t": "2022-01-01T09:31:00Z",
                    "o": 150.5
                    # Missing h, l, c, v
                },
                {  # Valid bar
                    "t": "2022-01-01T09:32:00Z",
                    "o": 151.5,
                    "h": 152.5,
                    "l": 151.0,
                    "c": 152.0,
                    "v": 8000
                }
            ],
            "symbol": "AAPL"
        }

        result = historical_fetcher._parse_bars_response(response, "AAPL")

        # Should only have 2 valid bars
        assert len(result) == 2
        assert result[0].o == 150.0
        assert result[1].o == 151.5

    @pytest.mark.asyncio
    @patch('app.stocks.historical_data.httpx.AsyncClient')
    async def test_fetch_historical_bars_success(self, mock_client_class, historical_fetcher, sample_alpaca_response):
        """Test successful fetch of historical bars"""
        # Mock httpx.AsyncClient response
        mock_response = Mock()
        mock_response.json.return_value = sample_alpaca_response
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_client_class.return_value = mock_client

        # Fetch historical bars
        result = await historical_fetcher.fetch_historical_bars(
            symbol="AAPL",
            timeframe="1Min",
            limit=3
        )

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(bar, BarData) for bar in result)
        assert result[0].S == "AAPL"

    @pytest.mark.asyncio
    @patch('app.stocks.historical_data.httpx.AsyncClient')
    async def test_fetch_historical_bars_with_dates(self, mock_client_class, historical_fetcher, sample_alpaca_response):
        """Test fetch with explicit start and end dates"""
        mock_response = Mock()
        mock_response.json.return_value = sample_alpaca_response
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_client_class.return_value = mock_client

        start = datetime(2022, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        end = datetime(2022, 1, 1, 16, 0, 0, tzinfo=timezone.utc)

        result = await historical_fetcher.fetch_historical_bars(
            symbol="AAPL",
            timeframe="1Min",
            start=start,
            end=end
        )

        # Verify API was called with correct params
        call_args = mock_client.get.call_args
        assert "AAPL" in call_args[0][0]
        assert call_args[1]['params']['timeframe'] == "1Min"

    @pytest.mark.asyncio
    @patch('app.stocks.historical_data.httpx.AsyncClient')
    async def test_fetch_historical_bars_defaults_to_24h(self, mock_client_class, historical_fetcher, sample_alpaca_response):
        """Test that fetch defaults to last 24 hours if no dates provided"""
        mock_response = Mock()
        mock_response.json.return_value = sample_alpaca_response
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_client_class.return_value = mock_client

        result = await historical_fetcher.fetch_historical_bars(symbol="AAPL")

        # Should succeed with defaults
        assert isinstance(result, list)

        # Verify params had start/end times
        call_args = mock_client.get.call_args
        params = call_args[1]['params']
        assert 'start' in params
        assert 'end' in params

    @pytest.mark.asyncio
    @patch('app.stocks.historical_data.httpx.AsyncClient')
    async def test_fetch_historical_bars_http_error(self, mock_client_class, historical_fetcher):
        """Test handling of HTTP errors"""
        import httpx

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )

        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)  # Don't suppress exceptions
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_client_class.return_value = mock_client

        result = await historical_fetcher.fetch_historical_bars(symbol="AAPL")

        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    @patch('app.stocks.historical_data.httpx.AsyncClient')
    async def test_fetch_historical_bars_request_error(self, mock_client_class, historical_fetcher):
        """Test handling of request errors (network issues)"""
        import httpx

        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)  # Don't suppress exceptions
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("Network error"))

        mock_client_class.return_value = mock_client

        result = await historical_fetcher.fetch_historical_bars(symbol="AAPL")

        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    @patch('app.stocks.historical_data.httpx.AsyncClient')
    async def test_fetch_historical_bars_timeout(self, mock_client_class, historical_fetcher):
        """Test handling of timeout errors"""
        import asyncio

        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)  # Don't suppress exceptions
        mock_client.get = AsyncMock(side_effect=asyncio.TimeoutError())

        mock_client_class.return_value = mock_client

        result = await historical_fetcher.fetch_historical_bars(symbol="AAPL")

        # Should return empty list on timeout
        assert result == []

    def test_bardata_to_candle_dict_conversion(self, historical_fetcher, sample_alpaca_response):
        """Test that BarData can be converted to candle dict format"""
        bars = historical_fetcher._parse_bars_response(sample_alpaca_response, "AAPL")

        candle_dict = bars[0].to_candle_dict()

        assert candle_dict['open'] == 150.0
        assert candle_dict['high'] == 151.0
        assert candle_dict['low'] == 149.5
        assert candle_dict['close'] == 150.5
        assert candle_dict['volume'] == 10000
        assert candle_dict['timestamp'] == "2022-01-01T09:30:00Z"
        assert candle_dict['trade_count'] == 50
        assert candle_dict['vwap'] == 150.25

    @pytest.mark.asyncio
    @patch('app.stocks.historical_data.httpx.AsyncClient')
    async def test_different_timeframes(self, mock_client_class, historical_fetcher, sample_alpaca_response):
        """Test fetching with different timeframes"""
        mock_response = Mock()
        mock_response.json.return_value = sample_alpaca_response
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_client_class.return_value = mock_client

        timeframes = ["1Min", "5Min", "15Min", "1Hour", "1Day"]

        for timeframe in timeframes:
            result = await historical_fetcher.fetch_historical_bars(
                symbol="AAPL",
                timeframe=timeframe
            )

            assert isinstance(result, list)
            # Verify timeframe was passed correctly
            call_args = mock_client.get.call_args
            assert call_args[1]['params']['timeframe'] == timeframe


@pytest.mark.asyncio
async def test_historical_data_integration():
    """Integration test for historical data fetching (requires valid API keys)"""
    # Skip this test in CI/CD without real credentials
    pytest.skip("Requires valid Alpaca API credentials")

    # This test would be run manually with real credentials
    fetcher = AlpacaHistoricalData(
        api_key="your_real_api_key",
        api_secret="your_real_api_secret"
    )

    result = await fetcher.fetch_historical_bars(
        symbol="AAPL",
        timeframe="1Min",
        limit=10
    )

    assert isinstance(result, list)
    assert len(result) <= 10
    assert all(isinstance(bar, BarData) for bar in result)
