"""Broker routes for snaptrade integration

Snaptrade has its own SDK for python integration"""

from logging import getLogger
from typing import Optional

import httpx
from app.auth import get_current_user_id
from app.database.external_database_manager import DatabaseManager
from app.dependencies import get_brokerage_client, get_supabase_db
from fastapi import APIRouter, Depends, HTTPException, Query
from snaptrade_client import SnapTrade

logger = getLogger(__name__)

broker_route = APIRouter(prefix="/brokerages")


@broker_route.post("/register")
def register_user(
    user_id: str = Depends(get_current_user_id),
    client: SnapTrade = Depends(get_brokerage_client),
    db: DatabaseManager = Depends(get_supabase_db),
):
    """Register a new user with SnapTrade and store their user_secret."""
    try:
        register_response = client.authentication.register_snap_trade_user(
            body={"userId": user_id}
        )
        user_secret = register_response.body["userSecret"]

        # Store the user_secret in database
        db.store_snaptrade_user(user_id, user_secret)

        return {
            "status": "registered",
            "user_id": user_id,
            "message": "User registered with SnapTrade successfully",
        }
    except NotImplementedError:
        # DB stub not implemented yet - return user_secret for manual storage
        return {
            "status": "registered",
            "user_id": user_id,
            "user_secret": user_secret,
            "message": "User registered. Store this user_secret securely (DB storage not yet implemented)",
        }
    except httpx.HTTPStatusError as e:
        error_detail = str(e)
        status_code = e.response.status_code if e.response else 502
        raise HTTPException(
            status_code=status_code, detail=f"Failed to register user: {error_detail}"
        ) from e


@broker_route.get("/login_url")
def get_login_url(
    redirect_uri: Optional[str] = Query(None, description="Redirect URI after auth"),
    user_id: str = Depends(get_current_user_id),
    client: SnapTrade = Depends(get_brokerage_client),
    db: DatabaseManager = Depends(get_supabase_db),
):
    """Get a redirect URL for users to connect their brokerage accounts."""
    try:
        # Get user_secret from database
        user_secret = db.get_snaptrade_user_secret(user_id)
        if not user_secret:
            raise HTTPException(
                status_code=404,
                detail="User not registered with SnapTrade. Call /register first.",
            )

        query_params = {"userId": user_id, "userSecret": user_secret}
        if redirect_uri:
            query_params["customRedirect"] = redirect_uri

        login_response = client.authentication.login_snap_trade_user(
            query_params=query_params
        )

        return {
            "redirect_url": login_response.body,
            "message": "Redirect user to this URL to connect their brokerage",
        }
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail="Database storage not yet implemented. User secret retrieval unavailable.",
        ) from None
    except httpx.HTTPStatusError as e:
        error_detail = str(e)
        status_code = e.response.status_code if e.response else 502
        raise HTTPException(
            status_code=status_code, detail=f"Failed to get login URL: {error_detail}"
        ) from e


@broker_route.get("/holdings")
def get_holdings(
    account_id: Optional[str] = Query(None, description="Specific account ID to get holdings for"),
    user_id: str = Depends(get_current_user_id),
    client: SnapTrade = Depends(get_brokerage_client),
    db: DatabaseManager = Depends(get_supabase_db),
):
    """Get holdings for the authenticated user. If account_id is provided, returns holdings for that account only. Otherwise returns holdings for all accounts."""
    try:
        # Get user_secret from database
        user_secret = db.get_snaptrade_user_secret(user_id)
        if not user_secret:
            raise HTTPException(
                status_code=404,
                detail="User not registered with SnapTrade. Call /register first.",
            )

        query_params = {"userId": user_id, "userSecret": user_secret}

        if account_id:
            # Get holdings for specific account
            holdings_response = client.account_information.get_user_holdings(
                account_id=account_id,
                query_params=query_params,
            )
            return {
                "holdings": [holdings_response.body],
                "user_id": user_id,
            }

        # Get all accounts first, then fetch holdings for each
        accounts_response = client.account_information.list_user_accounts(
            query_params=query_params
        )

        all_holdings = []
        for account in accounts_response.body:
            acc_id = account.get("id") if isinstance(account, dict) else getattr(account, "id", None)
            if acc_id:
                holdings = client.account_information.get_user_holdings(
                    account_id=acc_id,
                    query_params=query_params,
                )
                all_holdings.append(holdings.body)

        return {
            "holdings": all_holdings,
            "user_id": user_id,
        }
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail="Database storage not yet implemented. User secret retrieval unavailable.",
        ) from None
    except httpx.HTTPStatusError as e:
        error_detail = str(e)
        status_code = e.response.status_code if e.response else 502
        raise HTTPException(
            status_code=status_code, detail=f"Failed to get holdings: {error_detail}"
        ) from e


@broker_route.delete("/user")
def delete_user(
    user_id: str = Depends(get_current_user_id),
    client: SnapTrade = Depends(get_brokerage_client),
    db: DatabaseManager = Depends(get_supabase_db),
):
    """Delete a user from SnapTrade and remove local records."""
    try:
        # Delete from SnapTrade
        delete_response = client.authentication.delete_snap_trade_user(
            query_params={"userId": user_id}
        )

        # Delete from local database
        try:
            db.delete_snaptrade_user(user_id)
        except NotImplementedError:
            logger.warning("DB delete not implemented, skipping local cleanup")

        return {
            "status": "deleted",
            "user_id": user_id,
            "snaptrade_response": delete_response.body,
            "message": "User deleted from SnapTrade successfully",
        }
    except httpx.HTTPStatusError as e:
        error_detail = str(e)
        status_code = e.response.status_code if e.response else 502
        raise HTTPException(
            status_code=status_code, detail=f"Failed to delete user: {error_detail}"
        ) from e
