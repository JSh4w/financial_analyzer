"""Routes for Trading212 API integration."""

from __future__ import annotations

from logging import getLogger

import requests
from app.auth import get_current_user_id
from app.config import Settings
from app.database.external_database_manager import DatabaseManager
from app.dependencies import get_supabase_db
from app.utilities.cache import SimpleCache
from fastapi import APIRouter, Depends, HTTPException
from models.t212_models import T212SummaryResponse

settings = Settings()
logger = getLogger(__name__)

t212_router = APIRouter()

# Global cache instance for T212 API responses
_t212_cache = SimpleCache()


@t212_router.get("/T212_add_user_keys")
async def add_user_keys_t212(
    db: DatabaseManager = Depends(get_supabase_db),
    user_id: str = Depends(get_current_user_id),
    user_secret: str = None,
    user_key: str = None,
):
    """
    Store Trading212 API keys for the authenticated user.
    Args:
        db (DatabaseManager): Database manager instance.
        user_id (str): Authenticated user ID from JWT token.
        user_secret (str): Trading212 API secret key.
        user_key (str): Trading212 API key ID.
    Returns: None.
    """
    data = {
        "user_id": user_id,
        "t212_key_id": db.encrypt_string(user_key),
        "t212_key_secret": db.encrypt_string(user_secret),
    }
    db.client.table("t212").upsert(data).execute()


@t212_router.get("/T212_remove_user_keys")
async def remove_user_keys_t212(
    db: DatabaseManager = Depends(get_supabase_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Remove Trading212 API keys for the authenticated user.
    Args:
        db (DatabaseManager): Database manager instance.
        user_id (str): Authenticated user ID from JWT token.
    Returns: None.
    """
    db.client.table("t212").delete().eq("user_id", user_id).execute()


@t212_router.get("/T212_summary")
def get_t212_account_summary(
    db: DatabaseManager = Depends(get_supabase_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Provides a breakdown of your account's cash and investment metrics,
    including available funds, invested capital, and total account value.

    Rate limit: 1 req / 5s
    Cache TTL: 6 seconds (slightly longer than rate limit)

    Args:
        user_id: Authenticated user ID from JWT token

    Returns:
        dict: Account summary with cash and investment metrics

    Raises:
        HTTPException: If the API request fails
    """
    # Check cache first (6 second TTL to respect 5s rate limit)
    cache_key = f"t212_summary_{user_id}"
    cached_data = _t212_cache.get(cache_key, ttl=6)
    if cached_data:
        logger.info("Returning cached T212 summary for user %s", user_id)
        return cached_data

    try:
        data = (
            db.client.table("t212")
            .select("*")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        t212_key_id = db.decrypt_string(data.data["t212_key_id"])
        t212_key_secret = db.decrypt_string(data.data["t212_key_secret"])
        if not data or not data.data:
            raise HTTPException(
                status_code=404,
                detail="Trading212 API keys not found for the user.",
            )
        url = "https://live.trading212.com/api/v0/equity/account/summary"
        auth = (t212_key_id, t212_key_secret)
        headers = {"Authorization": t212_key_id}
        response = requests.get(url, headers=headers, auth=auth, timeout=5)
        response.raise_for_status()
        raw_data = response.json()

        # Transform to frontend format
        transformed_data = T212SummaryResponse.from_t212_api(raw_data)
        result_dict = transformed_data.model_dump()

        # Cache the transformed response
        _t212_cache.set(cache_key, result_dict)
        logger.info("Fetched and cached T212 summary for user %s", user_id)

        return result_dict
    except requests.exceptions.Timeout as e:
        logger.error("T212 API timeout for user %s: %s", user_id, str(e))
        raise HTTPException(
            status_code=504, detail="Trading212 API request timed out"
        ) from e

    except requests.exceptions.HTTPError as e:
        logger.error("T212 API HTTP error for user %s: %s", user_id, str(e))
        status_code = e.response.status_code if e.response else 500

        # Handle rate limiting specifically
        if status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait a few seconds before trying again.",
            ) from e

        raise HTTPException(
            status_code=status_code, detail=f"Trading212 API error: {str(e)}"
        ) from e

    except requests.exceptions.RequestException as e:
        logger.error("T212 API request failed for user %s: %s", user_id, str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch Trading212 data: {str(e)}"
        ) from e


@t212_router.get("/T212_positions")
def get_t212_account_positions(
    db: DatabaseManager = Depends(get_supabase_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Fetch all open positions for your account

    Rate limit: 1 req / 1s
    Cache TTL: 2 seconds (slightly longer than rate limit)

    Args:
        user_id: Authenticated user ID from JWT token

    Returns:
        dict: Account positions data

    Raises:
        HTTPException: If the API request fails
    """
    # Check cache first (2 second TTL to respect 1s rate limit)
    cache_key = f"t212_positions_{user_id}"
    cached_data = _t212_cache.get(cache_key, ttl=2)
    if cached_data:
        logger.info("Returning cached T212 positions for user %s", user_id)
        return cached_data

    try:
        data = (
            db.client.table("t212")
            .select("*")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if not data or not data.data:
            raise HTTPException(
                status_code=404,
                detail="Trading212 API keys not found for the user.",
            )

        t212_key_id = db.decrypt_string(data.data["t212_key_id"])
        t212_key_secret = db.decrypt_string(data.data["t212_key_secret"])

        url = "https://live.trading212.com/api/v0/equity/positions"
        auth = (t212_key_id, t212_key_secret)
        headers = {"Authorization": t212_key_id}
        response = requests.get(url, headers=headers, auth=auth, timeout=5)
        response.raise_for_status()
        result = response.json()

        # Cache the successful response
        _t212_cache.set(cache_key, result)
        logger.info("Fetched and cached T212 positions for user %s", user_id)

        return result

    except requests.exceptions.Timeout as e:
        logger.error("T212 API timeout for user %s: %s", user_id, str(e))
        raise HTTPException(
            status_code=504, detail="Trading212 API request timed out"
        ) from e

    except requests.exceptions.HTTPError as e:
        logger.error("T212 API HTTP error for user %s: %s", user_id, str(e))
        status_code = e.response.status_code if e.response else 500

        # Handle rate limiting specifically
        if status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Trading212 allows 1 request per second.",
            ) from e

        raise HTTPException(
            status_code=status_code, detail=f"Trading212 API error: {str(e)}"
        ) from e

    except requests.exceptions.RequestException as e:
        logger.error("T212 API request failed for user %s: %s", user_id, str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch Trading212 data: {str(e)}"
        ) from e
