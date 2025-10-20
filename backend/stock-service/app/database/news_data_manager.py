from database.connection import DuckDBConnection
import logging 

logger = logging.getLogger(__name__)


class NewsDataManager:
    """Handles all news article data operations"""
    def __init__(self, db_connection):
        """
        Args:
            db_connection: DuckDBConnection isinstance
        """
        self.db_connection = db_connection or DuckDBConnection
        self.conn = self.db_connection.get_connection()