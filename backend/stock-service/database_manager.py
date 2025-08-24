"""Database handler to connect to Supabase"""
import logging
from supabase import create_client, Client
from app.config import Settings
from models.user_models import User
from models.stock_models import DailyStockData

logger = logging.getLogger(__name__)
settings = Settings()

class DatabaseManager:
    """Handlers collating and sending data models to the database"""
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.client: Client = None

    def connect(self) -> bool:
        """Initialize Supabase client"""
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Connected to Supabase")
            return True
        except Exception as e:
            logger.error("Failed to connect to Supabase: %s", e)
            return False

    def insert_historic_stock_data(self, stock_data: DailyStockData) -> bool:
        """Insert stock price data"""
        try:
            data = stock_data.model_dump()
            result = self.client.table("stock_data").insert(data).execute()
            logger.info("Stock added: %s", result)
            return True
        except Exception as e:
            logger.error("Failed to insert stock data: %s", e)
            return False
    
    def bulk_insert_historic_stock_data(self, stock_data_list: list[DailyStockData]) -> bool:
        """Insert multiple stock price records at once"""
        try:
            data_list = [stock_data.model_dump() for stock_data in stock_data_list]
            result = self.client.table("stock_data").insert(data_list).execute()
            logger.info("Bulk inserted %d stock records", len(data_list))
            return True
        except Exception as e:
            logger.error("Failed to bulk insert stock data: %s", e)
            return False

    def get_stock_data(self, symbol: str, limit: int = 100):
        """Get stock data for a symbol"""
        try:
            result = self.client.table("stock_prices").select("*").eq("symbol", symbol).order("date", desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error("Failed to get stock data: %s", e)
            return None

    def create_user_profile(self, user: User):
        """Create user profile"""
        try:
            data = user.model_dump()
            result = self.client.table("user_profiles").insert(data).execute()
            return result.data
        except Exception as e:
            logger.error("Failed to create user profile: %s", e)
            return None

    def update_watchlist(self, user_id: str, watchlist: list):
        """Update user watchlist"""
        try:
            result = self.client.table("user_profiles").update({"watchlist": watchlist}).eq("id", user_id).execute()
            return result.data
        except Exception as e:
            logger.error("Failed to update watchlist: %s", e)
            return None
