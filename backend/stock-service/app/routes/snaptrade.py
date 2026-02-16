"""Broker routes for snaptrade integration

Snaptrade has its own SDK for python integration"""

from logging import getLogger
from typing import Literal, Optional

import httpx
from app.auth import get_current_user_id
from app.database.external_database_manager import DatabaseManager
from app.dependencies import get_brokerage_client, get_supabase_db
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from snaptrade_client import SnapTrade

logger = getLogger(__name__)

broker_route = APIRouter(prefix="/brokerages")


class LoginUrlRequest(BaseModel):
    """Request body for generating connection portal URL."""

    broker: Optional[str] = None
    immediate_redirect: Optional[bool] = None
    custom_redirect: Optional[str] = None
    reconnect: Optional[str] = None
    connection_type: Optional[Literal["read", "trade", "trade-if-available"]] = None
    connection_portal_version: Optional[str] = None


def handle_snaptrade_error(e: httpx.HTTPStatusError, operation: str) -> HTTPException:
    """Parse SnapTrade API error responses and raise appropriate HTTPException.

    Handles error formats:
    - 400/404: {"default_detail": str, "default_code": int}
    - 500: {"detail": str, "status_code": int, "code": int}
    """
    status_code = e.response.status_code if e.response else 502

    try:
        error_body = e.response.json() if e.response else {}

        # Handle 400/404 error format
        if "default_detail" in error_body:
            detail = error_body.get("default_detail", str(e))
            code = error_body.get("default_code")
            error_msg = f"{operation}: {detail} (SnapTrade code: {code})" if code else f"{operation}: {detail}"

        # Handle 500 error format
        elif "detail" in error_body and "code" in error_body:
            detail = error_body.get("detail", str(e))
            code = error_body.get("code")
            error_msg = f"{operation}: {detail} (SnapTrade code: {code})" if code else f"{operation}: {detail}"

        # Fallback to string representation
        else:
            error_msg = f"{operation}: {str(e)}"

    except Exception:
        # If parsing fails, fall back to string representation
        error_msg = f"{operation}: {str(e)}"

    return HTTPException(status_code=status_code, detail=error_msg)


@broker_route.get("/list")
def list_brokerages(
    client: SnapTrade = Depends(get_brokerage_client),
):
    """List all available brokerages from SnapTrade."""
    try:
        response = client.reference_data.list_all_brokerages()
        brokerages = [
            {
                "id": b.get("id"),
                "slug": b.get("slug"),
                "name": b.get("name"),
                "display_name": b.get("display_name"),
                "logo_url": b.get("aws_s3_logo_url"),
                "square_logo_url": b.get("aws_s3_square_logo_url"),
                "enabled": b.get("enabled", False),
                "allows_trading": b.get("allows_trading", False),
            }
            for b in response.body
            if b.get("enabled") and not b.get("maintenance_mode")
        ]
        return {"brokerages": brokerages}
    except httpx.HTTPStatusError as e:
        raise handle_snaptrade_error(e, "Failed to list brokerages") from e


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
    except httpx.HTTPStatusError as e:
        raise handle_snaptrade_error(e, "Failed to register user") from e


@broker_route.post("/login_url")
def get_login_url(
    config: LoginUrlRequest = Body(default_factory=LoginUrlRequest),
    user_id: str = Depends(get_current_user_id),
    client: SnapTrade = Depends(get_brokerage_client),
    db: DatabaseManager = Depends(get_supabase_db),
):
    """Get a redirect URL for users to connect their brokerage accounts.

    Configure the connection portal with options like broker selection, redirect URLs,
    dark mode, and connection permissions.
    """
    try:
        # Get user_secret from database, auto-register if not found
        user_secret = db.get_snaptrade_user_secret(user_id)
        if not user_secret:
            register_response = client.authentication.register_snap_trade_user(
                body={"userId": user_id}
            )
            user_secret = register_response.body["userSecret"]
            db.store_snaptrade_user(user_id, user_secret)

        # Build parameters for SnapTrade SDK - merge config with auth credentials
        login_params = {
            "user_id": user_id,
            "user_secret": user_secret,
            **config.model_dump(exclude_none=True),
        }

        login_response = client.authentication.login_snap_trade_user(**login_params)

        return {
            "redirect_url": login_response.body,
            "message": "Redirect user to this URL to connect their brokerage",
            "expires_in_minutes": 5,
        }
    except httpx.HTTPStatusError as e:
        raise handle_snaptrade_error(e, "Failed to get login URL") from e


@broker_route.get("/holdings")
def get_holdings(
    account_id: Optional[str] = Query(
        None, description="Specific account ID to get holdings for"
    ),
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
            acc_id = (
                account.get("id")
                if isinstance(account, dict)
                else getattr(account, "id", None)
            )
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
    except httpx.HTTPStatusError as e:
        raise handle_snaptrade_error(e, "Failed to get holdings") from e


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
        db.delete_snaptrade_user(user_id)

        return {
            "status": "deleted",
            "user_id": user_id,
            "snaptrade_response": delete_response.body,
            "message": "User deleted from SnapTrade successfully",
        }
    except httpx.HTTPStatusError as e:
        raise handle_snaptrade_error(e, "Failed to delete user") from e
