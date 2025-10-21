from pathlib import Path
import logging
import duckdb

logger = logging.getLogger(__name__)

class DuckDBConnection:
    """Singleton class to handle DuckDB data for all operations"""

    def __init__(self, db_path= "data/stock_data.duckdb"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        logger.info("DuckDB connected: %s",db_path)
    
    def get_connection(self):
        """Return the connection"""
        return self.conn      
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close() 
            logger.info("DuckDB connection closed")