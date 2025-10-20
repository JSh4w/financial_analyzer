"""DuckDB manager for stock market data storage and retrieval"""
from pathlib import Path
from typing import Dict, Any, List, Tuple
import logging
from database.connection import DuckDBConnection


logger = logging.getLogger(__name__)

class StockDataManager:
    def __init__(self, db_connection):
        """
        Args:
            db_connection: DuckDBConnection instance
        """
        self.db_connection = db_connection or DuckDBConnection
        self.conn = self.db_connection.get_connection()
        self._create_tables()

    def _create_tables(self):
        """Create database tables with proper schema"""
        # Main OHLCV table - partitioned by symbol for fast queries
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_1m (
                symbol VARCHAR NOT NULL,
                minute_timestamp VARCHAR NOT NULL,
                open DOUBLE NOT NULL,
                high DOUBLE NOT NULL,
                low DOUBLE NOT NULL,
                close DOUBLE NOT NULL,
                volume BIGINT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, minute_timestamp)
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_time
            ON ohlcv_1m (symbol, minute_timestamp DESC)
        """)

        # Raw trades table (optional - for detailed analysis)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                symbol VARCHAR NOT NULL,
                price DOUBLE NOT NULL,
                volume BIGINT NOT NULL,
                timestamp VARCHAR NOT NULL,
                trade_conditions VARCHAR[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        logger.info("DuckDB tables created")

    def upsert_candle(self, symbol: str, minute_timestamp: str, candle_data: Dict[str, Any]):
        """Insert or update a single minute candle"""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO ohlcv_1m
                (symbol, minute_timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                symbol, minute_timestamp,
                candle_data['open'],
                candle_data['high'],
                candle_data['low'],
                candle_data['close'],
                candle_data['volume']
            ])
        except Exception as e:
            logger.error(f"Failed to upsert candle for {symbol}: {e}")

    def bulk_upsert_candles(self, symbol: str, candles_dict: Dict[str, Dict[str, Any]]):
        """Efficiently insert/update multiple candles for a symbol"""
        if not candles_dict:
            return

        try:
            data = [
                (symbol, timestamp, candle['open'], candle['high'],
                 candle['low'], candle['close'], candle['volume'])
                for timestamp, candle in candles_dict.items()
            ]

            self.conn.executemany("""
                INSERT OR REPLACE INTO ohlcv_1m
                (symbol, minute_timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data)

            logger.debug(f"Bulk upserted {len(data)} candles for {symbol}")
        except Exception as e:
            logger.error(f"Failed bulk upsert for {symbol}: {e}")

    def get_recent_candles(self, symbol: str, limit: int = 1440) -> Dict[str, Dict[str, Any]]:
        """Get recent candles for a symbol, ordered by timestamp DESC"""
        try:
            result = self.conn.execute("""
                SELECT minute_timestamp, open, high, low, close, volume
                FROM ohlcv_1m
                WHERE symbol = ?
                ORDER BY minute_timestamp DESC
                LIMIT ?
            """, [symbol, limit]).fetchall()

            # Convert to dictionary format matching your current structure
            return {
                row[0]: {
                    'open': row[1], 'high': row[2], 'low': row[3],
                    'close': row[4], 'volume': row[5]
                }
                for row in result
            }
        except Exception as e:
            logger.error(f"Failed to get candles for {symbol}: {e}")
            return {}

    def insert_trade(self, symbol: str, price: float, volume: int, timestamp: str, conditions: List[str] = None):
        """Insert individual trade record"""
        try:
            self.conn.execute("""
                INSERT INTO trades (symbol, price, volume, timestamp, trade_conditions)
                VALUES (?, ?, ?, ?, ?)
            """, [symbol, price, volume, timestamp, conditions or []])
        except Exception as e:
            logger.error(f"Failed to insert trade for {symbol}: {e}")

    def export_to_parquet(self, symbol: str, output_dir: str = "exports") -> str:
        """Export symbol data to parquet for long-term storage"""
        Path(output_dir).mkdir(exist_ok=True)
        output_file = f"{output_dir}/{symbol}_ohlcv.parquet"

        try:
            self.conn.execute(f"""
                COPY (
                    SELECT * FROM ohlcv_1m
                    WHERE symbol = '{symbol}'
                    ORDER BY minute_timestamp
                ) TO '{output_file}' (FORMAT 'parquet')
            """)
            logger.info(f"Exported {symbol} to {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Failed to export {symbol}: {e}")
            return None

    def get_symbols_stats(self) -> List[Tuple]:
        """Get statistics for all tracked symbols"""
        try:
            return self.conn.execute("""
                SELECT
                    symbol,
                    COUNT(*) as candle_count,
                    MIN(minute_timestamp) as first_candle,
                    MAX(minute_timestamp) as last_candle,
                    MAX(updated_at) as last_updated
                FROM ohlcv_1m
                GROUP BY symbol
                ORDER BY symbol
            """).fetchall()
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return []

    def get_candle_count(self, symbol: str = None) -> int:
        """Get total candle count for a symbol or all symbols"""
        try:
            if symbol:
                result = self.conn.execute("""
                    SELECT COUNT(*) FROM ohlcv_1m WHERE symbol = ?
                """, [symbol]).fetchone()
            else:
                result = self.conn.execute("SELECT COUNT(*) FROM ohlcv_1m").fetchone()

            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get candle count: {e}")
            return 0

    def cleanup_old_data(self, days_to_keep: int = 30, time_from: str = None):
        """Remove data older than specified days
        
        Args:
            days_to_keep: Number of days to keep
            time_from: Reference time as RFC-3339 string (e.g., "2022-01-01T00:00:00Z")
        """
        try:
            from datetime import datetime, timedelta
            
            # Handle time_from parameter
            if time_from is None:
                cutoff_dt = datetime.now() - timedelta(days=days_to_keep)
            else:
                # Parse RFC-3339 format
                reference_dt = datetime.fromisoformat(time_from.replace('Z', '+00:00'))
                cutoff_dt = reference_dt - timedelta(days=days_to_keep)
            
            # Convert cutoff to RFC-3339 string
            cutoff_timestamp = cutoff_dt.isoformat().replace('+00:00', 'Z')

            deleted = self.conn.execute("""
                DELETE FROM ohlcv_1m WHERE minute_timestamp < ?
            """, [cutoff_timestamp]).fetchone()

            logger.info(f"Cleaned up data older than {days_to_keep} days from {cutoff_timestamp}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return None

    def get_candles_by_time_range(self, symbol: str, from_timestamp: str, to_timestamp: str) -> Dict[str, Dict[str, Any]]:
        """Get candles within a specific time range (for TradingView historical data)

        Args:
            symbol: Stock symbol
            from_timestamp: Start time in RFC-3339 format (e.g., "2021-02-22T15:51:44Z")
            to_timestamp: End time in RFC-3339 format

        Returns:
            Dictionary of timestamp -> OHLCV data, sorted ascending by time
        """
        try:
            result = self.conn.execute("""
                SELECT minute_timestamp, open, high, low, close, volume
                FROM ohlcv_1m
                WHERE symbol = ?
                AND minute_timestamp >= ?
                AND minute_timestamp <= ?
                ORDER BY minute_timestamp ASC
            """, [symbol, from_timestamp, to_timestamp]).fetchall()

            return {
                row[0]: {
                    'open': row[1], 'high': row[2], 'low': row[3],
                    'close': row[4], 'volume': row[5]
                }
                for row in result
            }
        except Exception as e:
            logger.error(f"Failed to get candles by time range for {symbol}: {e}")
            return {}

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("DuckDB connection closed")