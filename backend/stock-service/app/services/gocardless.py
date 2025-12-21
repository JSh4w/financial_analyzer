"""GoCardless API client for handling user authentication and data retrieval."""
from datetime import datetime, timedelta
from decimal import Decimal
import httpx

class GoCardlessClient:
    """
    GoCardless class for getting user information
    Handles token creation and usage
    """
    def __init__(self, secret_id: str, secret_key: str):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.refresh_expires: datetime | None = None
        self.access_expires: datetime | None = None 

    async def get_token(self) -> str:
        " Get valid access token, refreshing or creating as needed."
        # Buffer of 60 seconds before expiry
        # short temp token 
        if self.access_token and self.access_expires > datetime.now() + timedelta(seconds=60):
            return self.access_token

        # user longer refresh token
        if self.refresh_token:
            await self._refresh()
        # get new token using env vars
        else:
            await self._new_token()

        return self.access_token

    async def _new_token(self):
        # POST /api/v2/token/new/ with secret_id/key
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://bankaccountdata.gocardless.com/api/v2/token/new/",
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json"
                },
                json={
                    "secret_id": self.secret_id,
                    "secret_key": self.secret_key
                }
            )
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access"]
            self.refresh_token = data["refresh"]
            self.refresh_expires = datetime.now() + timedelta(seconds=data["refresh_expires"])
            self.access_expires = datetime.now() + timedelta(seconds=data["access_expires"])

    async def _refresh(self):
        # POST /api/v2/token/refresh/ with refresh_token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://bankaccountdata.gocardless.com/api/v2/token/refresh/",
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json"
                },
                json={
                    "refresh": self.refresh_token
                }
            )
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access"]
            self.access_expires = datetime.now() + timedelta(seconds=data["access_expires"])
    
    async def get_institutions(self) -> list[dict]:
        """Returns list of available institutions."""
        token = await self.get_token()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://bankaccountdata.gocardless.com/api/v2/institutions/",
                params={"country": "gb"},
                headers={
                    "accept": "application/json",
                    "Authorization": f"Bearer {token}",
                },
            )
            response.raise_for_status()
            data = response.json()

        # Normalize response to a list of institution dicts
        if isinstance(data, dict):
            for key in ("results", "institutions", "data"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            # If we get a single dict back, wrap it in a list
            return [data]
        if isinstance(data, list):
            return data
        return []
            

    async def create_requisition(self, redirect_uri: str, institution_id: str, user_id: str | None = None) -> dict:
        """Creates a requisition and returns the authorization link and requisition ID."""
        token = await self.get_token()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://bankaccountdata.gocardless.com/api/v2/requisitions/",
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json={
                    "redirect": redirect_uri,
                    "institution_id": institution_id,
                    "reference": user_id or "user_ref",
                    "user_language": "EN",
                }
            )
            response.raise_for_status()
            data = response.json()
            return {
                "requisition_id": data["id"],
                "link": data["link"]
            }


    async def get_balance(self, account_id: str) -> Decimal:
        ...