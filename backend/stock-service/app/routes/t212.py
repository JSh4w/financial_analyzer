from __future__ import annotations
from logging import getLogger 

from fastapi import APIRouter, Depends

import requests
from app.config import Settings
from app.auth import get_current_user_id

settings = Settings()
logger = getLogger(__name__)

t212_router = APIRouter()

@t212_router.get("/T212")
def get_t212_data(
    #_ : str = Depends(get_current_user_id)
    ):
    """
        Provides user T212 data based on user_id 
    """
    API_KEY = settings.T212_KEY_ID
    API_SECRET = settings.T212_SECRET_KEY
    url = "https://live.trading212.com/api/v0/equity/account/summary"
    response = requests.get(url, auth=(API_KEY, API_SECRET), timeout=10)
    data = response.json()
    return data