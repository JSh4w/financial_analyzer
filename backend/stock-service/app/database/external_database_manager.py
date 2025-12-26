"""Database handler to connect to Supabase"""
import logging
from datetime import datetime, timedelta, timezone

from app.config import Settings
from models.user_models import User
from models.stock_models import DailyStockData

from supabase import create_client, Client

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

    def get_stock_data(self, symbol: str, limit: int = 100) -> list[DailyStockData]:
        """Get stock data for a symbol"""
        try:
            result = self.client.table("stock_prices").select("*").eq("symbol", symbol).order("date", desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error("Failed to get stock data: %s", e)
            return None

    def create_user_profile(self, user: User) -> dict | None:
        """Create user profile"""
        try:
            data = user.model_dump()
            result = self.client.table("user_profiles").insert(data).execute()
            return result.data
        except Exception as e:
            logger.error("Failed to create user profile: %s", e)
            return None

    def get_user_profile(self, user_id: str) -> dict | None:
        """Get user profile by user_id"""
        try:
            result = self.client.table("user_profiles").select("*").eq("id", user_id).single().execute()
            return result.data
        except Exception as e:
            logger.error("Failed to get user profile: %s", e)
            return None

    def update_user_profile(self, user_id: str, updates: dict) -> dict | None:
        """Update user profile"""
        try:
            result = self.client.table("user_profiles").update(updates).eq("id", user_id).execute()
            return result.data
        except Exception as e:
            logger.error("Failed to update user profile: %s", e)
            return None

    def update_watchlist(self, user_id: str, watchlist: list) -> dict | None:
        """Update user watchlist"""
        try:
            result = self.client.table("user_profiles").update({"watchlist": watchlist}).eq("id", user_id).execute()
            return result.data
        except Exception as e:
            logger.error("Failed to update watchlist: %s", e)
            return None

    def store_bank_requisition(
            self,
            user_id: str,
            requisition_id: str,
            institution_id: str,
            reference: str,
        ) -> dict | None:
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

    def get_user_requisitions(self, user_id: str) -> list[dict] | None:
        """Get all bank requisitions for a user"""
        try:
            result = self.client.table("bank_requisitions").select("*").eq("user_id", user_id).execute()
            return result.data
        except Exception as e:
            logger.error("Failed to get requisitions: %s", e)
            return None

    def get_balance_details_for_account(self, user_id: str, account_id: str) -> dict | None:
        """Get stored balance details for a bank account"""
        try:
            result = self.client.table("bank_account_balances").select("*").eq("account_id", account_id).single().execute()
            return result.data
        except Exception as e:
            logger.error("Failed to get balance details: %s", e)
            return None

    def can_refresh_balance(self, account_id: str) -> bool:
        """Check if balance data can be refreshed based on rate limits"""
        try:
            result = self.client.table("bank_account_balances").select("can_refresh_at").eq("account_id", account_id).single().execute()
            if not result.data or not result.data.get("can_refresh_at"):
                return True

            can_refresh_at = datetime.fromisoformat(result.data["can_refresh_at"].replace("Z", "+00:00"))
            current_time = datetime.now(timezone.utc)

            return current_time >= can_refresh_at
        except Exception as e:
            logger.error("Failed to check refresh status: %s", e)
            return True

    def store_or_update_balance(
        self,
        user_id: str,
        account_id: str,
        balances: list[dict],
        rate_limit_reset_seconds: int | None = None,
        rate_limit_remaining: int | None = None,
    ) -> dict | None:
        """Store or update bank account balance data with rate limit tracking"""
        try:
            now = datetime.now(timezone.utc)
            can_refresh_at = None

            if rate_limit_reset_seconds:
                can_refresh_at = now + timedelta(seconds=rate_limit_reset_seconds)

            data = {
                "user_id": user_id,
                "account_id": account_id,
                "balances": balances,
                "last_fetched_at": now.isoformat(),
                "can_refresh_at": can_refresh_at.isoformat() if can_refresh_at else None,
                "rate_limit_remaining": rate_limit_remaining,
                "rate_limit_reset_seconds": rate_limit_reset_seconds,
            }

            existing = self.client.table("bank_account_balances").select("id").eq("account_id", account_id).execute()

            if existing.data and len(existing.data) > 0:
                result = self.client.table("bank_account_balances").update(data).eq("account_id", account_id).execute()
                logger.info("Updated balance for account: %s", account_id)
            else:
                result = self.client.table("bank_account_balances").insert(data).execute()
                logger.info("Stored new balance for account: %s", account_id)

            return result.data
        except Exception as e:
            logger.error("Failed to store/update balance: %s", e)
            return None



#
#
#{
# "balances": [
#   {
#     "balanceAmount": {
#       "amount": "271.0600",
#       "currency": "GBP"
#     },
#     "balanceType": "closingAvailable",
#     "referenceDate": "2025-11-12"
#   }
# ]
#}
#
#