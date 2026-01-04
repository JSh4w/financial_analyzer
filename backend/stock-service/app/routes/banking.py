"""Banking routes for GoCardless integration"""
from fastapi import APIRouter, Request, Depends, HTTPException
import httpx

from app.services.gocardless import GoCardlessClient
from app.auth import get_current_user_id
from app.database.external_database_manager import DatabaseManager
from app.dependencies import (
    get_supabase_db,
    get_banking_client,
)

from logging import getLogger 
logger = getLogger(__name__)


banking_router = APIRouter(prefix="/banking")

@banking_router.post("/link")
async def link_bank(client : GoCardlessClient = Depends(get_banking_client)):
    """Generate a bank linking URL for the user."""
    url = await client.create_requisition(...)
    return {"url": url}

@banking_router.get("/get_token")
async def get_token(client: GoCardlessClient = Depends(get_banking_client)):
    """Get current GoCardless access token"""
    token = await client.get_token()
    return {"token": token}


@banking_router.get("/me")
async def get_current_user_info(
    user_id: str = Depends(get_current_user_id),
    db : DatabaseManager = Depends(get_supabase_db)
):
    """Test endpoint to verify user_id extraction from JWT token"""
    # Try to get user profile
    profile = db.get_user_profile(user_id)

    return {
        "user_id": user_id,
        "profile": profile,
        "message": "Successfully extracted user_id from JWT token"
    }

@banking_router.get("/institutions")
async def list_institutions(client: GoCardlessClient = Depends(get_banking_client)):
    """Get list of available banking institutions"""
    institutions = await client.get_institutions()
    # Return the complete list of institutions as provided by the client
    return {"institutions": institutions}

@banking_router.post("/requisition")
async def requisition(
    redirect_uri: str,
    institution_id: str,
    user_id: str = Depends(get_current_user_id),
    client: GoCardlessClient = Depends(get_banking_client),
    db: DatabaseManager = Depends(get_supabase_db),
):
    """Create a GoCardless requisition and return the authentication link."""
    try:
        # Create requisition with GoCardless
        result = await client.create_requisition(redirect_uri, institution_id, user_id)
        requisition_id = result["requisition_id"]
        auth_link = result["link"]

        # Store requisition in database
        db.store_bank_requisition(
            user_id=user_id,
            requisition_id=requisition_id,
            institution_id=institution_id,
            reference=result["reference"]
        )

        return {
            "link": auth_link,
            "requisition_id": requisition_id
        }
    except httpx.HTTPStatusError as e:
        # Extract error details from the response
        error_detail = str(e)
        status_code = e.response.status_code if e.response else 500

        raise HTTPException(
            status_code=status_code,
            detail=f"Failed to create bank requisition: {error_detail}"
        ) from e

@banking_router.get("/requisition/{requisition_id}")
async def get_requisition_status(
    requisition_id: str,
    user_id: str = Depends(get_current_user_id),
    client: GoCardlessClient = Depends(get_banking_client),
    db: DatabaseManager = Depends(get_supabase_db),
):
    """Get requisition details including status and auth link if needed."""
    try:
        # Verify requisition belongs to user
        requisitions = db.get_user_requisitions(user_id)
        if not any(req["requisition_id"] == requisition_id for req in requisitions):
            raise HTTPException(status_code=404, detail="Requisition not found")

        # Get full details from GoCardless
        details = await client.get_requisition_details(requisition_id)

        return {
            "requisition_id": details.get("id"),
            "status": details.get("status"),
            "institution_id": details.get("institution_id"),
            "link": details.get("link"),
            "accounts": details.get("accounts", []),
            "created": details.get("created"),
        }
    except httpx.HTTPStatusError as e:
        error_detail = str(e)
        status_code = e.response.status_code if e.response else 500
        raise HTTPException(
            status_code=status_code,
            detail=f"Failed to retrieve requisition: {error_detail}"
        ) from e

@banking_router.get("/all_balances")
async def get_all_balances(
    user_id: str = Depends(get_current_user_id),
    client: GoCardlessClient = Depends(get_banking_client),
    db: DatabaseManager = Depends(get_supabase_db),
):
    """Get all bank account balances for the current user."""
    try:
        # Retrieve all requisitions for the user
        requisitions = db.get_user_requisitions(user_id)
        logger.info(f"Found {len(requisitions)} requisitions for user {user_id}")

        pending_requisitions = []

        # Maps: account_id -> institution_name and account_id -> list of balances
        account_to_institution = {}
        account_to_balances = {}

        for req in requisitions:
            requisition_id = req["requisition_id"]

            # Get full requisition details to check status
            requisition_details = await client.get_requisition_details(requisition_id)
            status = requisition_details.get("status")
            institution_id = requisition_details.get("institution_id")

            logger.info("Requisition %s status: %s", requisition_id, status)

            # Handle based on status
            if status == "LN":  # Linked - accounts are available
                account_ids = requisition_details.get("accounts", [])
                if account_ids:
                    # Get institution name
                    institution_name = await client.get_institution_name(institution_id)

                    for account_id in account_ids:
                        account_to_balances[account_id] = []
                        account_to_institution[account_id] = institution_name
                else:
                    logger.warning(f"Requisition {requisition_id} is linked but has no accounts")

            elif status in ["GC", "CR", "UA"]:  # Give Consent, Created, or Undergoing Authentication - user needs to authenticate
                institution_name = await client.get_institution_name(institution_id) if institution_id else "Unknown"
                pending_requisitions.append({
                    "requisition_id": requisition_id,
                    "institution_id": institution_id,
                    "institution_name": institution_name,
                    "status": status,
                    "link": requisition_details.get("link"),
                    "message": "Please complete authentication by visiting the link"
                })
            else:
                # Other statuses (EX - Expired, RJ - Rejected, etc.)
                logger.warning(f"Requisition {requisition_id} has status {status}")
                institution_name = await client.get_institution_name(institution_id) if institution_id else "Unknown"
                pending_requisitions.append({
                    "requisition_id": requisition_id,
                    "institution_id": institution_id,
                    "institution_name": institution_name,
                    "status": status,
                    "message": f"Requisition status: {status}"
                })

        # Fetch balances for all unique accounts in one go (deduplicated)
        accounts_list = list(account_to_balances.keys())
        if accounts_list:
            logger.info(f"Fetching balances for {len(accounts_list)} unique accounts")
            needs_refresh = []

            # Check each account for cached data and rate limit status
            for account in accounts_list:
                account_balance = db.get_balance_details_for_account(account)

                if account_balance and not db.can_refresh_balance(account):
                    # Use cached data - rate limit still active
                    logger.info(f"Using cached balance for account {account} (rate limit active)")
                    account_to_balances[account].extend(account_balance.get("balances", []))
                else:
                    # Need to fetch fresh data (no cache or can refresh)
                    needs_refresh.append(account)

            # Fetch fresh data for accounts that need it
            if needs_refresh:
                logger.info(f"Fetching fresh balances for {len(needs_refresh)} accounts")
                fresh_balance_information = await client.get_balance_from_accounts(needs_refresh)

                for balance_info in fresh_balance_information:
                    account_id = balance_info.get("account_id")
                    if not account_id:
                        logger.warning("Balance info missing account_id, skipping")
                        continue

                    # Store in DB with rate limit tracking
                    db.store_or_update_balance(
                        user_id=user_id,
                        account_id=account_id,
                        balances=balance_info.get("balances", []),
                        rate_limit_reset_seconds=balance_info.get("rate_limit_reset_seconds"),
                        rate_limit_remaining=balance_info.get("rate_limit_remaining"),
                    )

                    # Add to response
                    account_to_balances[account_id].extend(balance_info.get("balances", []))

        # Group balances by institution name instead of account_id
        institution_to_balances = {}
        for account_id, balances in account_to_balances.items():
            institution_name = account_to_institution.get(account_id, "Unknown Bank")
            if institution_name not in institution_to_balances:
                institution_to_balances[institution_name] = []
            institution_to_balances[institution_name].extend(balances)

        return {
            "balances": institution_to_balances,
            "pending_requisitions": pending_requisitions
        }
    except httpx.HTTPStatusError as e:
        error_detail = str(e)
        status_code = e.response.status_code if e.response else 500

        raise HTTPException(
            status_code=status_code,
            detail=f"Failed to retrieve balances: {error_detail}"
        ) from e
