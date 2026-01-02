from __future__ import annotations

from logging import getLogger

import requests
from app.config import Settings
from fastapi import APIRouter, HTTPException

settings = Settings()
logger = getLogger(__name__)

t212_router = APIRouter()


@t212_router.get("/T212_summary")
def get_t212_account_summary():
    """
    Provides a breakdown of your account's cash and investment metrics,
    including available funds, invested capital, and total account value.

    Rate limit: 1 req / 5s

    Args:
        user_id: Authenticated user ID from JWT token

    Returns:
        dict: Account summary with cash and investment metrics

    Raises:
        HTTPException: If the API request fails
    """
    try:
        url = "https://live.trading212.com/api/v0/equity/account/summary"
        auth = (settings.T212_KEY_ID, settings.T212_SECRET_KEY)
        headers = {"Authorization": settings.T212_KEY_ID}
        response = requests.get(url, headers=headers, auth=auth, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        logger.error(f"T212 API request failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch Trading212 data: {str(e)}"
        ) from e


@t212_router.get("/T212_positions")
def get_t212_account_positions():
    """
    Fetch all open positions for your account

    Rate limit: 1 req / 1s

    Args:
        user_id: Authenticated user ID from JWT token

    Returns:
        dict: Account summary with cash and investment metrics

    Raises:
        HTTPException: If the API request fails
    """
    try:
        url = "https://live.trading212.com/api/v0/equity/positions"
        auth = (settings.T212_KEY_ID, settings.T212_SECRET_KEY)
        headers = {"Authorization": settings.T212_KEY_ID}
        response = requests.get(url, headers=headers, auth=auth, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        logger.error(f"T212 API request failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch Trading212 data: {str(e)}"
        ) from e

        # except requests.exceptions.Timeout as e:
        #     logger.error(f"T212 API timeout for user {user_id}: {str(e)}")
        #     raise HTTPException(
        #         status_code=504, detail="Trading212 API request timed out"
        #     ) from e

        # except requests.exceptions.HTTPError as e:
        #     logger.error(f"T212 API HTTP error for user {user_id}: {str(e)}")
        #     status_code = e.response.status_code if e.response else 500

        #     # Handle rate limiting specifically
        #     if status_code == 429:
        #         raise HTTPException(
        #             status_code=429,
        #             detail="Rate limit exceeded. Trading212 allows 1 request per 5 seconds.",
        #         ) from e

        #     raise HTTPException(
        #         status_code=status_code, detail=f"Trading212 API error: {str(e)}"
        #     ) from e

        # except requests.exceptions.RequestException as e:
        #     logger.error(f"T212 API request failed for user {user_id}: {str(e)}")
        #     raise HTTPException(
        #         status_code=500, detail=f"Failed to fetch Trading212 data: {str(e)}"
        #     ) from e
