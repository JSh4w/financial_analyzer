"""Test TradingView API endpoints"""
import pytest
from datetime import datetime, timezone, timedelta


def test_tradingview_config(client):
    """Test TradingView config endpoint"""
    response = client.get("/api/tradingview/config")
    assert response.status_code == 200

    data = response.json()
    assert "supported_resolutions" in data
    assert "1" in data["supported_resolutions"]
    assert data["supports_time"] is True


def test_tradingview_symbol_info(client):
    """Test symbol info endpoint"""
    response = client.get("/api/tradingview/symbol_info?symbol=AAPL")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "AAPL"
    assert data["ticker"] == "AAPL"
    assert data["has_intraday"] is True
    assert data["timezone"] == "America/New_York"


def test_tradingview_history_no_data(client):
    """Test history endpoint with no data available"""
    # Use timestamps far in the future where no data exists
    future = datetime.now(timezone.utc) + timedelta(days=365)
    from_ts = int(future.timestamp())
    to_ts = int((future + timedelta(hours=1)).timestamp())

    response = client.get(
        f"/api/tradingview/history?symbol=NONEXISTENT&from_ts={from_ts}&to_ts={to_ts}"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["s"] == "no_data"


def test_tradingview_history_with_data(client, db_manager):
    """Test history endpoint with existing data"""
    # Insert test data
    symbol = "TEST"
    now = datetime.now(timezone.utc)

    test_candles = {}
    for i in range(5):
        timestamp = (now - timedelta(minutes=i)).replace(second=0, microsecond=0)
        timestamp_str = timestamp.isoformat().replace('+00:00', 'Z')
        test_candles[timestamp_str] = {
            'open': 100.0 + i,
            'high': 101.0 + i,
            'low': 99.0 + i,
            'close': 100.5 + i,
            'volume': 1000 * i
        }

    db_manager.bulk_upsert_candles(symbol, test_candles)

    # Query the data
    from_ts = int((now - timedelta(hours=1)).timestamp())
    to_ts = int(now.timestamp())

    response = client.get(
        f"/api/tradingview/history?symbol={symbol}&from_ts={from_ts}&to_ts={to_ts}"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["s"] == "ok"
    assert len(data["t"]) == 5
    assert len(data["o"]) == 5
    assert len(data["h"]) == 5
    assert len(data["l"]) == 5
    assert len(data["c"]) == 5
    assert len(data["v"]) == 5

    # Verify data is sorted ascending by time
    assert data["t"] == sorted(data["t"])

    # Verify data values
    assert all(isinstance(t, int) for t in data["t"])
    assert all(isinstance(o, float) for o in data["o"])


def test_tradingview_history_time_range(client, db_manager):
    """Test history endpoint respects time range"""
    symbol = "RANGE_TEST"
    base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    # Insert 60 minutes of data
    test_candles = {}
    for i in range(60):
        timestamp = (base_time + timedelta(minutes=i))
        timestamp_str = timestamp.isoformat().replace('+00:00', 'Z')
        test_candles[timestamp_str] = {
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000
        }

    db_manager.bulk_upsert_candles(symbol, test_candles)

    # Query only first 30 minutes
    from_ts = int(base_time.timestamp())
    to_ts = int((base_time + timedelta(minutes=30)).timestamp())

    response = client.get(
        f"/api/tradingview/history?symbol={symbol}&from_ts={from_ts}&to_ts={to_ts}"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["s"] == "ok"
    assert len(data["t"]) == 31  # Inclusive range: 0-30 minutes = 31 bars
