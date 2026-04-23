"""Custom investment models"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CustomInvestmentCreate(BaseModel):
    """Request body for creating a custom investment"""
    name: str
    description: Optional[str] = None
    amount: float


class CustomInvestment(BaseModel):
    """A stored custom investment entry"""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    amount: float
    created_at: Optional[datetime] = None
