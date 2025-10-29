"""Simple db handling for news information"""

import logging
from typing import Any, Dict, List, Optional

from app.database.connection import DuckDBConnection

logger = logging.getLogger(__name__)


class NewsDataManager:
    """Handles all news article data operations"""

    def __init__(self, db_connection):
        """
        Args:
            db_connection: DuckDBConnection instance
        """
        self.db_connection = db_connection or DuckDBConnection
        self.conn = self.db_connection.get_connection()
        self._create_news_table()

    def _create_news_table(self):
        """Create database tables with proper schema"""
        # Main OHLCV table - indexed by symbol for fast queries
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id BIGINT PRIMARY KEY,
                headline VARCHAR NOT NULL,
                summary VARCHAR,
                author VARCHAR,
                created_at VARCHAR NOT NULL,
                updated_at VARCHAR NOT NULL,
                url VARCHAR,
                content VARCHAR,
                symbols VARCHAR[],
                source VARCHAR,
                inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_created_at
            ON news (created_at DESC)
        """)
        logger.info("DuckDB news tables created")

    def insert_news(
        self,
        id: int,
        headline: str,
        created_at: str,
        symbols: Optional[List[str]] = None,
        summary: Optional[str] = None,
        author: Optional[str] = None,
        updated_at: Optional[str] = None,
        url: Optional[str] = None,
        content: Optional[str] = None,
        source: Optional[str] = None,
    ):
        """Insert or update a single minute candle"""
        try:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO news
                (id, headline, created_at, updated_at, symbols, summary author, url, content, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    id,
                    headline,
                    created_at,
                    updated_at,
                    symbols or [],
                    summary,
                    author,
                    url,
                    content,
                    source,
                ],
            )
        except Exception as e:
            logger.error("Failed to upsert candle for %s , $s", (symbols ,e))

    def get_news_by_symbol(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent news for a specific symbol"""
        try:
            result = self.conn.execute(
                """
                SELECT id, headline, summary, author, created_at, updated_at, url, symbols, source
                FROM news
                WHERE list_contains(symbols, ?)
                ORDER BY created_at DESC
                LIMIT ?
            """,
                [symbol, limit],
            ).fetchall()

            return [
                {
                    "id": row[0],
                    "headline": row[1],
                    "summary": row[2],
                    "author": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                    "url": row[6],
                    "symbols": row[7],
                    "source": row[8],
                }
                for row in result
            ]
        except Exception as e:
            logger.error("Failed to get news for %s : %s", symbol, e)
            return []

    def get_all_news(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all news articles ordered by most recent"""
        try:
            result = self.conn.execute(
                """
                SELECT id, headline, summary, author, created_at, updated_at, url, symbols, source
                FROM news
                ORDER BY created_at DESC
                LIMIT ?
            """,
                [limit],
            ).fetchall()

            return [
                {
                    "id": row[0],
                    "headline": row[1],
                    "summary": row[2],
                    "author": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                    "url": row[6],
                    "symbols": row[7],
                    "source": row[8],
                }
                for row in result
            ]
        except Exception as e:
            logger.error("Failed to get all news: %s",e)
            return []

    def close(self):
        """Close database connection"""
        if self.db_connection:
            self.db_connection.close()
