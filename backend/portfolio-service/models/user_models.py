"""Data models for user information"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class User(BaseModel): #using pydantic for type safety
    """User data"""
    id: int
    email: EmailStr
    username: str = Field(min_length=3, max_length=20)
    created_at: datetime
    is_active: bool = True
