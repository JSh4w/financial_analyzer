"""Banking routes for GoCardless integration"""
from fastapi import APIRouter, Request, Depends
from app.services.gocardless import GoCardlessClient
from app.auth import get_current_user_id
from app.database.external_database_manager import DatabaseManager

banking_router = APIRouter(prefix="/banking")

@banking_router.post("/link")
async def link_bank(request: Request):
    client: GoCardlessClient = request.app.state.banking_client
    url = await client.create_requisition(...)
    return {"url": url}

@banking_router.get("/get_token")
async def get_token(request: Request):
    client: GoCardlessClient = request.app.state.banking_client
    token = await client.get_token()
    return {"token": token}


@banking_router.get("/me")
async def get_current_user_info(
    request: Request,
    user_id: str = Depends(get_current_user_id)
):
    """Test endpoint to verify user_id extraction from JWT token"""
    db: DatabaseManager = request.app.state.supabase_db

    # Try to get user profile
    profile = db.get_user_profile(user_id)

    return {
        "user_id": user_id,
        "profile": profile,
        "message": "Successfully extracted user_id from JWT token"
    }

@banking_router.get("/institutions")
async def list_institutions(request: Request):
    """Get list of available banking institutions"""
    client: GoCardlessClient = request.app.state.banking_client
    institutions = await client.get_institutions()
    # Return the complete list of institutions as provided by the client
    return {"institutions": institutions}

@banking_router.post("/requisition")
async def requisition(
    request: Request,
    redirect_uri: str,
    institution_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Create a GoCardless requisition and return the authentication link."""
    client: GoCardlessClient = request.app.state.banking_client
    db: DatabaseManager = request.app.state.supabase_db

    # Create requisition with GoCardless
    result = await client.create_requisition(redirect_uri, institution_id, user_id)
    requisition_id = result["requisition_id"]
    auth_link = result["link"]

    # Store requisition in database
    db.store_bank_requisition(
        user_id=user_id,
        requisition_id=requisition_id,
        institution_id=institution_id
    )

    return {
        "link": auth_link,
        "requisition_id": requisition_id
    }
# @router.get("/balance")
# async def get_balance(request: Request):
#     client = request.app.state.gocardless
#     balance = await client.get_balance(account_id)
    # return {"balance": balance}