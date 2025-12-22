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

    def get_user_profile(self, user_id: str):
        """Get user profile by user_id"""
        try:
            result = self.client.table("user_profiles").select("*").eq("id", user_id).single().execute()
            return result.data
        except Exception as e:
            logger.error("Failed to get user profile: %s", e)
            return None

    def update_user_profile(self, user_id: str, updates: dict):
        """Update user profile"""
        try:
            result = self.client.table("user_profiles").update(updates).eq("id", user_id).execute()
            return result.data
        except Exception as e:
            logger.error("Failed to update user profile: %s", e)
            return None

    def update_watchlist(self, user_id: str, watchlist: list):
        """Update user watchlist"""
        try:
            result = self.client.table("user_profiles").update({"watchlist": watchlist}).eq("id", user_id).execute()
            return result.data
        except Exception as e:
            logger.error("Failed to update watchlist: %s", e)
            return None

    def store_bank_requisition(self, user_id: str, requisition_id: str, institution_id: str, reference: str):
        """Store GoCardless requisition for a user"""
        try:
            data = {
                "user_id": user_id,
                "requisition_id": requisition_id,
                "institution_id": institution_id,
                "reference": reference,
                "status": "pending",
                "created_at": "now()"
            }
            result = self.client.table("bank_requisitions").insert(data).execute()
            logger.info("Requisition stored: %s", requisition_id)
            return result.data
        except Exception as e:
            logger.error("Failed to store requisition: %s", e)
            return None

    def get_user_requisitions(self, user_id: str):
        """Get all bank requisitions for a user"""
        try:
            result = self.client.table("bank_requisitions").select("*").eq("user_id", user_id).execute()
            return result.data
        except Exception as e:
            logger.error("Failed to get requisitions: %s", e)
            return None
