"""Tests for DuckDB Manager - database operations for stock market data"""
import os
import shutil
import tempfile
from unittest.mock import patch, Mock

import pytest

from app.database.duckdb_manager import DuckDBManager


class TestDuckDBManager:
    """Test suite for DuckDBManager database operations"""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path for testing"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_stock_data.duckdb")
        yield db_path
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create DuckDBManager instance for testing"""
        manager = DuckDBManager(db_path=temp_db_path)
        yield manager
        manager.close()

    @pytest.fixture
    def sample_candle_data(self):
        """Sample OHLCV candle data for testing"""
        return {
            'open': 150.0,
            'high': 155.0,
            'low': 149.0,
            'close': 154.0,
            'volume': 1000000
        }

    @pytest.fixture
    def bulk_candle_data(self, base_timestamp):
        """Sample bulk candle data for testing"""
        return {
            base_timestamp: {
                'open': 150.0, 'high': 155.0, 'low': 149.0, 'close': 154.0, 'volume': 1000000
            },
            "2022-01-01T00:01:00Z": {
                'open': 154.0, 'high': 158.0, 'low': 153.0, 'close': 157.0, 'volume': 800000
            },
            "2022-01-01T00:02:00Z": {
                'open': 157.0, 'high': 160.0, 'low': 156.0, 'close': 159.0, 'volume': 900000
            }
        }

    def test_manager_initialization(self, temp_db_path):
        """Test DuckDBManager initializes correctly"""
        manager = DuckDBManager(db_path=temp_db_path)

        assert manager.db_path == temp_db_path
        assert manager.conn is not None
        assert os.path.exists(temp_db_path)

        manager.close()

    def test_database_directory_creation(self):
        """Test that database directory is created if it doesn't exist"""
        temp_dir = tempfile.mkdtemp()
        nested_path = os.path.join(temp_dir, "nested", "dir", "test.duckdb")

        manager = DuckDBManager(db_path=nested_path)

        assert os.path.exists(os.path.dirname(nested_path))
        assert os.path.exists(nested_path)

        manager.close()
        shutil.rmtree(temp_dir)

    def test_tables_creation(self, db_manager):
        """Test that required tables are created"""
        # Check ohlcv_1m table exists
        result = db_manager.conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='ohlcv_1m'
        """).fetchall()
        assert len(result) > 0

        # Check trades table exists
        result = db_manager.conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='trades'
        """).fetchall()
        assert len(result) > 0

    def test_upsert_single_candle(self, db_manager, sample_candle_data, base_timestamp):
        """Test inserting a single candle"""
        symbol = "AAPL"

        db_manager.upsert_candle(symbol, base_timestamp, sample_candle_data)

        # Verify data was inserted
        result = db_manager.conn.execute("""
            SELECT * FROM ohlcv_1m WHERE symbol = ? AND minute_timestamp = ?
        """, [symbol, base_timestamp]).fetchone()

        assert result is not None
        assert result[0] == symbol  # symbol
        assert result[1] == base_timestamp  # minute_timestamp
        assert result[2] == 150.0  # open
        assert result[3] == 155.0  # high
        assert result[4] == 149.0  # low
        assert result[5] == 154.0  # close
        assert result[6] == 1000000  # volume

    def test_upsert_candle_update(self, db_manager, base_timestamp):
        """Test updating an existing candle"""
        symbol = "AAPL"
        original_data = {'open': 150.0, 'high': 155.0, 'low': 149.0, 'close': 154.0, 'volume': 1000000}
        updated_data = {'open': 150.0, 'high': 156.0, 'low': 148.0, 'close': 155.0, 'volume': 1200000}

        # Insert original
        db_manager.upsert_candle(symbol, base_timestamp, original_data)

        # Update with new data
        db_manager.upsert_candle(symbol, base_timestamp, updated_data)

        # Verify only one record exists with updated values
        results = db_manager.conn.execute("""
            SELECT * FROM ohlcv_1m WHERE symbol = ? AND minute_timestamp = ?
        """, [symbol, base_timestamp]).fetchall()

        assert len(results) == 1
        result = results[0]
        assert result[3] == 156.0  # updated high
        assert result[4] == 148.0  # updated low
        assert result[5] == 155.0  # updated close
        assert result[6] == 1200000  # updated volume

    def test_bulk_upsert_candles(self, db_manager, bulk_candle_data):
        """Test bulk inserting multiple candles"""
        symbol = "GOOGL"

        db_manager.bulk_upsert_candles(symbol, bulk_candle_data)

        # Verify all candles were inserted
        results = db_manager.conn.execute("""
            SELECT COUNT(*) FROM ohlcv_1m WHERE symbol = ?
        """, [symbol]).fetchone()

        assert results[0] == 3

        # Verify data integrity
        all_results = db_manager.conn.execute("""
            SELECT minute_timestamp, open, high, low, close, volume
            FROM ohlcv_1m WHERE symbol = ? ORDER BY minute_timestamp
        """, [symbol]).fetchall()

        timestamps = list(bulk_candle_data.keys())
        timestamps.sort()

        for i, result in enumerate(all_results):
            expected_data = bulk_candle_data[timestamps[i]]
            assert result[0] == timestamps[i]
            assert result[1] == expected_data['open']
            assert result[2] == expected_data['high']
            assert result[3] == expected_data['low']
            assert result[4] == expected_data['close']
            assert result[5] == expected_data['volume']

    def test_bulk_upsert_empty_data(self, db_manager):
        """Test bulk upsert with empty data"""
        symbol = "EMPTY"

        # Should not raise exception
        db_manager.bulk_upsert_candles(symbol, {})

        # Verify no data was inserted
        result = db_manager.conn.execute("""
            SELECT COUNT(*) FROM ohlcv_1m WHERE symbol = ?
        """, [symbol]).fetchone()

        assert result[0] == 0

    def test_get_recent_candles(self, db_manager, bulk_candle_data):
        """Test retrieving recent candles"""
        symbol = "MSFT"

        # Insert test data
        db_manager.bulk_upsert_candles(symbol, bulk_candle_data)

        # Get recent candles
        recent_candles = db_manager.get_recent_candles(symbol, limit=2)

        assert len(recent_candles) == 2

        # Should be ordered by timestamp DESC (most recent first)
        timestamps = list(recent_candles.keys())
        assert timestamps[0] > timestamps[1]

        # Verify data structure
        for _, data in recent_candles.items():
            assert 'open' in data
            assert 'high' in data
            assert 'low' in data
            assert 'close' in data
            assert 'volume' in data

    def test_get_recent_candles_nonexistent_symbol(self, db_manager):
        """Test getting candles for non-existent symbol"""
        recent_candles = db_manager.get_recent_candles("NONEXISTENT")
        assert recent_candles == {}

    def test_insert_trade(self, db_manager, base_timestamp):
        """Test inserting individual trade record"""
        symbol = "TSLA"
        price = 800.0
        volume = 100
        conditions = ["T", "I"]

        db_manager.insert_trade(symbol, price, volume, base_timestamp, conditions)

        # Verify trade was inserted
        result = db_manager.conn.execute("""
            SELECT * FROM trades WHERE symbol = ? AND timestamp = ?
        """, [symbol, base_timestamp]).fetchone()

        assert result is not None
        assert result[0] == symbol
        assert result[1] == price
        assert result[2] == volume
        assert result[3] == base_timestamp
        # Note: trade_conditions might be stored differently in DuckDB

    def test_insert_trade_no_conditions(self, db_manager, base_timestamp):
        """Test inserting trade without conditions"""
        symbol = "AMZN"
        price = 3000.0
        volume = 50

        db_manager.insert_trade(symbol, price, volume, base_timestamp)

        # Verify trade was inserted
        result = db_manager.conn.execute("""
            SELECT * FROM trades WHERE symbol = ? AND timestamp = ?
        """, [symbol, base_timestamp]).fetchone()

        assert result is not None
        assert result[0] == symbol
        assert result[1] == price
        assert result[2] == volume

    def test_get_candle_count_specific_symbol(self, db_manager, bulk_candle_data):
        """Test getting candle count for specific symbol"""
        symbol = "COUNT_TEST"

        # Insert test data
        db_manager.bulk_upsert_candles(symbol, bulk_candle_data)

        count = db_manager.get_candle_count(symbol)
        assert count == 3

    def test_get_candle_count_all_symbols(self, db_manager, bulk_candle_data):
        """Test getting total candle count for all symbols"""
        # Insert data for multiple symbols
        db_manager.bulk_upsert_candles("SYMBOL1", bulk_candle_data)
        db_manager.bulk_upsert_candles("SYMBOL2", bulk_candle_data)

        total_count = db_manager.get_candle_count()
        assert total_count == 6  # 3 candles × 2 symbols

    def test_get_candle_count_nonexistent_symbol(self, db_manager):
        """Test getting candle count for non-existent symbol"""
        count = db_manager.get_candle_count("NONEXISTENT")
        assert count == 0

    def test_get_symbols_stats(self, db_manager, bulk_candle_data, base_timestamp):
        """Test getting statistics for all symbols"""
        # Insert data for multiple symbols
        db_manager.bulk_upsert_candles("STAT1", bulk_candle_data)

        # Add different timestamp data for another symbol
        other_data = {"2022-01-01T00:05:00Z": bulk_candle_data[base_timestamp]}
        db_manager.bulk_upsert_candles("STAT2", other_data)

        stats = db_manager.get_symbols_stats()

        assert len(stats) == 2

        # Find STAT1 in results
        stat1_result = None
        for stat in stats:
            if stat[0] == "STAT1":
                stat1_result = stat
                break

        assert stat1_result is not None
        assert stat1_result[1] == 3  # candle_count
        assert stat1_result[2] == base_timestamp  # first_candle (min timestamp)
        assert stat1_result[3] == "2022-01-01T00:02:00Z"  # last_candle (max timestamp)

    def test_get_symbols_stats_empty_database(self, db_manager):
        """Test getting stats from empty database"""
        stats = db_manager.get_symbols_stats()
        assert stats == []

    def test_cleanup_old_data(self, db_manager, base_timestamp):
        """Test cleaning up old data"""
        # Insert old and new data using string timestamps
        old_timestamp = "2021-11-22T00:00:00Z"  # 40 days ago from base
        new_timestamp = "2021-12-22T00:00:00Z"  # 10 days ago from base

        old_data = {'open': 100.0, 'high': 105.0, 'low': 99.0, 'close': 104.0, 'volume': 500000}
        new_data = {'open': 200.0, 'high': 205.0, 'low': 199.0, 'close': 204.0, 'volume': 600000}

        db_manager.upsert_candle("CLEANUP", old_timestamp, old_data)
        db_manager.upsert_candle("CLEANUP", new_timestamp, new_data)

        # Verify both records exist
        count_before = db_manager.get_candle_count("CLEANUP")
        assert count_before == 2

        # Cleanup data older than 30 days (you'll implement timestamp conversion in duckdb_manager)
        db_manager.cleanup_old_data(days_to_keep=30, time_from=base_timestamp)

        # Verify old data was removed
        count_after = db_manager.get_candle_count("CLEANUP")
        assert count_after == 1

        # Verify remaining data is the newer one
        remaining = db_manager.get_recent_candles("CLEANUP", limit=1)
        assert len(remaining) == 1
        timestamp = list(remaining.keys())[0]
        assert timestamp == new_timestamp

    def test_export_to_parquet(self, db_manager, bulk_candle_data):
        """Test exporting data to parquet format"""
        symbol = "EXPORT_TEST"

        # Insert test data
        db_manager.bulk_upsert_candles(symbol, bulk_candle_data)

        # Create temporary export directory
        temp_export_dir = tempfile.mkdtemp()

        try:
            # Export to parquet
            result_file = db_manager.export_to_parquet(symbol, temp_export_dir)

            assert result_file is not None
            expected_file = os.path.join(temp_export_dir, f"{symbol}_ohlcv.parquet")
            assert result_file == expected_file
            assert os.path.exists(result_file)

        finally:
            # Cleanup
            if os.path.exists(temp_export_dir):
                shutil.rmtree(temp_export_dir)

    def test_export_nonexistent_symbol(self, db_manager):
        """Test exporting non-existent symbol"""
        temp_export_dir = tempfile.mkdtemp()

        try:
            result_file = db_manager.export_to_parquet("NONEXISTENT", temp_export_dir)
            # Should still create the file (empty parquet)
            assert result_file is not None

        finally:
            if os.path.exists(temp_export_dir):
                shutil.rmtree(temp_export_dir)

    def test_close_connection(self, temp_db_path):
        """Test closing database connection"""
        manager = DuckDBManager(db_path=temp_db_path)
        assert manager.conn is not None

        manager.close()
        # After closing, connection should be None or closed
        # Note: DuckDB might not set conn to None, so we test that operations fail
        with pytest.raises(Exception):
            manager.conn.execute("SELECT 1")

    @patch('app.database.duckdb_manager.logger')
    def test_logging_on_error(self, mock_logger, db_manager):
        # Mock the entire connection instead of just execute method
        mock_conn = Mock()
        mock_conn.execute.side_effect = Exception("Test error")

        with patch.object(db_manager, 'conn', mock_conn):
            db_manager.upsert_candle("TEST", 123456789, {'invalid': 'data'})

        mock_logger.error.assert_called()


    def test_concurrent_operations(self, db_manager, base_timestamp):
        """Test that multiple operations can be performed concurrently"""
        import threading
        import time

        results = []
        errors = []

        def insert_data(symbol_suffix):
            try:
                symbol = f"CONCURRENT_{symbol_suffix}"
                data = {'open': 100.0, 'high': 105.0, 'low': 99.0, 'close': 104.0, 'volume': 500000}
                # Create unique timestamp for each thread
                from datetime import datetime, timedelta
                base_dt = datetime.fromisoformat(base_timestamp.replace('Z', '+00:00'))
                timestamp_dt = base_dt + timedelta(seconds=symbol_suffix)
                timestamp = timestamp_dt.isoformat().replace('+00:00', 'Z')
                db_manager.upsert_candle(symbol, timestamp, data)
                results.append(symbol)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=insert_data, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0
        assert len(results) == 5

        # Verify all data was inserted
        total_count = db_manager.get_candle_count()
        assert total_count == 5

    def test_large_dataset_performance(self, db_manager, base_timestamp):
        """Test performance with larger dataset"""
        symbol = "PERF_TEST"
        large_dataset = {}

        # Generate 1000 candles with RFC-3339 timestamps
        from datetime import datetime, timedelta
        base_dt = datetime.fromisoformat(base_timestamp.replace('Z', '+00:00'))
        
        for i in range(1000):
            timestamp_dt = base_dt + timedelta(minutes=i)  # 1 minute intervals
            timestamp = timestamp_dt.isoformat().replace('+00:00', 'Z')
            large_dataset[timestamp] = {
                'open': 100.0 + i * 0.1,
                'high': 105.0 + i * 0.1,
                'low': 99.0 + i * 0.1,
                'close': 104.0 + i * 0.1,
                'volume': 500000 + i * 1000
            }

        # Measure bulk insert time
        import time
        start_time = time.time()
        db_manager.bulk_upsert_candles(symbol, large_dataset)
        insert_time = time.time() - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert insert_time < 5.0  # 5 seconds threshold

        # Verify all data was inserted
        count = db_manager.get_candle_count(symbol)
        assert count == 1000

        # Test retrieval performance
        start_time = time.time()
        recent_candles = db_manager.get_recent_candles(symbol, limit=100)
        retrieval_time = time.time() - start_time

        assert retrieval_time < 1.0  # 1 second threshold
        assert len(recent_candles) == 100