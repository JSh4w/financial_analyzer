"""Stock models for historic information"""
from pydantic import BaseModel


class User(BaseModel):
    """Main user creation model
    User_id should be from Supabase authentication"""
    user_id : str
    user_name : str    