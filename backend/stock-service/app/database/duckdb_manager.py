"""DuckDB manager for stock market data storage and retrieval"""
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
import logging
import duckdb

logger = logging.getLogger(__name__)

class DuckDBManager:
    def __init__(self, db_path="data/stock_data.duckdb"):
        # Create data directory if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self._create_tables()
        logger.info(f"DuckDB connected: {db_path}")

    def _create_tables(self):
        """Create database tables with proper schema"""
        # Main OHLCV table - partitioned by symbol for fast queries
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_1m (
                symbol VARCHAR NOT NULL,
                minute_timestamp BIGINT NOT NULL,
                open DOUBLE NOT NULL,
                high DOUBLE NOT NULL,
                low DOUBLE NOT NULL,
                close DOUBLE NOT NULL,
                volume BIGINT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, minute_timestamp)
            )
        """)

        # Create index for fast timestamp ordering
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
                timestamp BIGINT NOT NULL,
                trade_conditions VARCHAR[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        logger.info("DuckDB tables created")

    def upsert_candle(self, symbol: str, minute_timestamp: int, candle_data: Dict[str, Any]):
        """Insert or update a single minute candle"""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO ohlcv_1m
                (symbol, minute_timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                symbol,
                minute_timestamp,
                candle_data['open'],
                candle_data['high'],
                candle_data['low'],
                candle_data['close'],
                candle_data['volume']
            ])
        except Exception as e:
            logger.error(f"Failed to upsert candle for {symbol}: {e}")

    def bulk_upsert_candles(self, symbol: str, candles_dict: Dict[int, Dict[str, Any]]):
        """Efficiently insert/update multiple candles for a symbol"""
        if not candles_dict:
            return

        try:
            # Prepare data for bulk insert
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

    def get_recent_candles(self, symbol: str, limit: int = 1440) -> Dict[int, Dict[str, Any]]:
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

    def insert_trade(self, symbol: str, price: float, volume: int, timestamp: int, conditions: List[str] = None):
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

    def cleanup_old_data(self, days_to_keep: int = 30, time_from: float = time.time()):
        """Remove data older than specified days, with optional time_from"""
        try:
            cutoff_timestamp = time_from - (days_to_keep * 24 * 60 * 60* 1000)

            deleted = self.conn.execute("""
                DELETE FROM ohlcv_1m WHERE minute_timestamp < ?
            """, [cutoff_timestamp]).fetchone()

            logger.info(f"Cleaned up data older than {days_to_keep} days")
            return deleted
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("DuckDB connection closed")