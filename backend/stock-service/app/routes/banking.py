"""Banking routes for GoCardless integration"""
from fastapi import APIRouter, Request, Depends, HTTPException
from app.services.gocardless import GoCardlessClient
from app.auth import get_current_user_id
from app.database.external_database_manager import DatabaseManager
import httpx

from app.dependencies import (
    get_db_manager,
    get_banking_client
)

banking_router = APIRouter(prefix="/banking")

@banking_router.post("/link")
async def link_bank(client : GoCardlessClient = Depends(get_banking_client)):
    url = await client.create_requisition(...)
    return {"url": url}

@banking_router.get("/get_token")
async def get_token(client: GoCardlessClient = Depends(get_banking_client)):
    token = await client.get_token()
    return {"token": token}


@banking_router.get("/me")
async def get_current_user_info(
    user_id: str = Depends(get_current_user_id),
    db : DatabaseManager = Depends(get_db_manager)
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
    request: Request,
    redirect_uri: str,
    institution_id: str,
    user_id: str = Depends(get_current_user_id),
    client: GoCardlessClient = Depends(get_banking_client),
    db: DatabaseManager = Depends(get_db_manager),
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
        )
# @router.get("/balance")
# async def get_balance(request: Request):
#     client = request.app.state.gocardless
#     balance = await client.get_balance(account_id)
    # return {"balance": balance}