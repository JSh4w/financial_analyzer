"""Routes for managing custom investment amounts"""

from logging import getLogger

from app.auth import get_current_user_id
from app.database.external_database_manager import DatabaseManager
from app.dependencies import get_supabase_db
from fastapi import APIRouter, Depends, HTTPException
from models.investment_models import CustomInvestment, CustomInvestmentCreate

logger = getLogger(__name__)

investments_router = APIRouter(prefix="/investments")


@investments_router.post("", response_model=CustomInvestment, status_code=201)
async def create_investment(
    body: CustomInvestmentCreate,
    user_id: str = Depends(get_current_user_id),
    db: DatabaseManager = Depends(get_supabase_db),
):
    """Create a new custom investment for the current user."""
    try:
        result = db.add_custom_investment(
            user_id=user_id,
            name=body.name,
            amount=body.amount,
            description=body.description,
        )
    except Exception as exc:
        logger.exception("Failed to store investment for user %s", user_id)
        raise HTTPException(
            status_code=500, detail="Failed to store investment"
        ) from exc

    if not result:
        raise HTTPException(status_code=500, detail="Failed to store investment")
    return result


@investments_router.get("", response_model=list[CustomInvestment])
async def get_investments(
    user_id: str = Depends(get_current_user_id),
    db: DatabaseManager = Depends(get_supabase_db),
):
    """Retrieve all custom investments for the current user."""
    try:
        return db.get_custom_investments(user_id)
    except Exception as exc:
        logger.exception("Failed to retrieve investments for user %s", user_id)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve investments"
        ) from exc


@investments_router.delete("/{investment_id}", status_code=204)
async def delete_investment(
    investment_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DatabaseManager = Depends(get_supabase_db),
):
    """Delete a custom investment by ID for the current user."""
    try:
        deleted = db.delete_custom_investment(investment_id, user_id)
    except Exception as exc:
        logger.exception("Failed to delete investment %s", investment_id)
        raise HTTPException(
            status_code=500, detail="Failed to delete investment"
        ) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Investment not found")
