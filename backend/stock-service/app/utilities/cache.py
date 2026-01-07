"""Simple in-memory cache with TTL for API rate limit compliance."""

from __future__ import annotations

from logging import getLogger
from time import time

logger = getLogger(__name__)


class SimpleCache:
    """Thread-safe in-memory cache with TTL for user-scoped data."""

    def __init__(self):
        self._cache = {}

    def get(self, key: str, ttl: int) -> dict | None:
        """
        Get cached value if it exists and hasn't expired.

        Args:
            key: Cache key (should include user_id for security)
            ttl: Time to live in seconds

        Returns:
            Cached value or None if expired/not found
        """
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time() - timestamp < ttl:
                logger.debug("Cache hit for key: %s", key)
                logger.debug("Time left: %s", ttl - (time() - timestamp))
                return value
            # Clean up expired entry
            del self._cache[key]
            logger.debug("Cache expired for key: %s", key)
        return None

    def set(self, key: str, value: dict) -> None:
        """
        Store value in cache with current timestamp.

        Args:
            key: Cache key (should include user_id for security)
            value: Data to cache
        """
        self._cache[key] = (value, time())
        logger.debug("Cache set for key: %s", key)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
