"""Persistent Subscription Manager for user stock subscriptions in database"""

import logging
import time
from typing import List, Optional

from app.database.external_database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class PersistentSubscriptionManager:
    """Manages persistent user subscriptions in PostgreSQL/Supabase"""

    def __init__(self, db: DatabaseManager):
        self.db = db
        # Optional: In-memory cache for active symbols (refreshed every 60s)
        self._active_symbols_cache: Optional[List[str]] = None
        self._cache_timestamp: Optional[float] = None

    def subscribe_user(self, user_id: str, symbol: str) -> bool:
        """
        Add or reactivate a user's subscription to a symbol

        Args:
            user_id: UUID of the user
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            True if subscription was created/reactivated, False otherwise
        """
        try:
            symbol = symbol.upper()

            # Insert or update subscription
            response = (
                self.db.client.table("user_subscriptions")
                .upsert(
                    {
                        "user_id": user_id,
                        "symbol": symbol,
                        "is_active": True,
                        "last_active_at": "now()",
                    },
                    on_conflict="user_id,symbol",
                )
                .execute()
            )

            # Invalidate cache
            self._active_symbols_cache = None

            logger.info(f"User {user_id} subscribed to {symbol}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe user {user_id} to {symbol}: {e}")
            return False

    def unsubscribe_user(self, user_id: str, symbol: str) -> bool:
        """
        Mark subscription as inactive (soft delete)

        Args:
            user_id: UUID of the user
            symbol: Stock symbol

        Returns:
            True if subscription was deactivated, False otherwise
        """
        try:
            symbol = symbol.upper()

            response = (
                self.db.client.table("user_subscriptions")
                .update({"is_active": False, "last_active_at": "now()"})
                .eq("user_id", user_id)
                .eq("symbol", symbol)
                .execute()
            )

            # Invalidate cache
            self._active_symbols_cache = None

            logger.info(f"User {user_id} unsubscribed from {symbol}")
            return True

        except Exception as e:
            logger.error(f"Failed to unsubscribe user {user_id} from {symbol}: {e}")
            return False

    def get_user_subscriptions(self, user_id: str) -> List[str]:
        """
        Get all active symbols for a user

        Args:
            user_id: UUID of the user

        Returns:
            List of stock symbols (e.g., ['AAPL', 'TSLA'])
        """
        try:
            response = (
                self.db.client.table("user_subscriptions")
                .select("symbol")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .order("last_active_at", desc=True)
                .execute()
            )

            symbols = [row["symbol"] for row in response.data]
            logger.info(f"Retrieved {len(symbols)} subscriptions for user {user_id}")
            return symbols

        except Exception as e:
            logger.error(f"Failed to get subscriptions for user {user_id}: {e}")
            return []

    def get_active_symbols(self, use_cache: bool = True) -> List[str]:
        """
        Get all symbols with at least one active subscriber
        Uses caching to reduce database load (cache refreshes every 60 seconds)

        Args:
            use_cache: Whether to use cached results (default: True)

        Returns:
            List of unique stock symbols with active subscribers
        """
        # Check cache (refresh every 60 seconds)
        if (
            use_cache
            and self._active_symbols_cache is not None
            and self._cache_timestamp is not None
        ):
            now = time.time()
            if now - self._cache_timestamp < 60:
                return self._active_symbols_cache

        try:
            # Query distinct symbols with active subscriptions
            response = (
                self.db.client.table("user_subscriptions")
                .select("symbol")
                .eq("is_active", True)
                .execute()
            )

            # Get unique symbols
            symbols = list(set([row["symbol"] for row in response.data]))

            # Update cache
            self._active_symbols_cache = symbols
            self._cache_timestamp = time.time()

            logger.info(f"Retrieved {len(symbols)} active symbols from database")
            return symbols

        except Exception as e:
            logger.error(f"Failed to get active symbols: {e}")
            return []

    def get_symbol_subscriber_count(self, symbol: str) -> int:
        """
        Get number of active subscribers for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Number of active subscribers
        """
        try:
            symbol = symbol.upper()
            response = (
                self.db.client.table("user_subscriptions")
                .select("id", count="exact")
                .eq("symbol", symbol)
                .eq("is_active", "true")
                .execute()
            )

            count = response.count if response.count is not None else 0
            logger.debug(f"Subscriber count for {symbol}: {count}")
            return count

        except Exception as e:
            logger.error(f"Failed to get subscriber count for {symbol}: {e}")
            return 0

    def should_unsubscribe_from_alpaca(self, symbol: str) -> bool:
        """
        Check if symbol should be unsubscribed from Alpaca (no active users)

        Args:
            symbol: Stock symbol

        Returns:
            True if no active subscribers exist, False otherwise
        """
        return self.get_symbol_subscriber_count(symbol) == 0

    def update_last_active(self, user_id: str, symbol: str) -> bool:
        """
        Update last active timestamp (for connection health tracking)

        Args:
            user_id: UUID of the user
            symbol: Stock symbol

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            symbol = symbol.upper()

            response = (
                self.db.client.table("user_subscriptions")
                .update({"last_active_at": "now()"})
                .eq("user_id", user_id)
                .eq("symbol", symbol)
                .execute()
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to update last_active for user {user_id}, symbol {symbol}: {e}"
            )
            return False

    def cleanup_inactive_subscriptions(self, days_inactive: int = 30) -> int:
        """
        Clean up subscriptions that haven't been active for a specified number of days

        Args:
            days_inactive: Number of days of inactivity before cleanup (default: 30)

        Returns:
            Number of subscriptions cleaned up
        """
        try:
            # This would require a more complex query with date comparison
            # For now, just return 0 (implement if needed later)
            logger.info("Cleanup not implemented yet")
            return 0

        except Exception as e:
            logger.error(f"Failed to cleanup inactive subscriptions: {e}")
            return 0
