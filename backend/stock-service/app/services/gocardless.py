"""GoCardless API client for handling user authentication and data retrieval."""
from datetime import datetime, timedelta
from typing import List
import httpx
import uuid

from logging import getLogger
logger = getLogger(__name__)

class GoCardlessClient:
    """
    GoCardless class for getting user information
    Handles token creation and usage
    """
    def __init__(
            self, secret_id: str, 
            secret_key: str,
            http_client: httpx.AsyncClient | None = None
        ):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.client: httpx.AsyncClient | None = http_client
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

    async def _new_token(self) -> None:
        # POST /api/v2/token/new/ with secret_id/key
        response = await self.client.post(
                "/api/v2/token/new/",
                headers={"Content-Type": "application/json"},
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

    async def _refresh(self) -> None:
        # POST /api/v2/token/refresh/ with refresh_token
        response = await self.client.post(
            "/api/v2/token/refresh/",
            headers={
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
    
    async def get_institutions(self) -> List[dict]:
        """Returns list of available institutions."""
        token = await self.get_token()

        response = await self.client.get(
            "/api/v2/institutions/",
            params={"country": "gb"},
            headers={
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

    async def get_institution_name(self, institution_id: str) -> str:
        """Get institution name by ID"""
        token = await self.get_token()
        try:
            response = await self.client.get(
                f"/api/v2/institutions/{institution_id}/",
                headers={
                    "Authorization": f"Bearer {token}",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("name", institution_id)
        except Exception as e:
            logger.warning("Failed to get institution name for %s: %s", institution_id, e)
            return institution_id

    async def create_requisition(self, redirect_uri: str, institution_id: str, user_id: str | None = None) -> dict:
        """Creates a requisition and returns the authorization link and requisition ID."""
        token = await self.get_token()
        reference = str(uuid.uuid4())
        response = await self.client.post(
            "/api/v2/requisitions/",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json={
                "redirect": redirect_uri,
                "institution_id": institution_id,
                "reference": reference or user_id or "anonymous",
                "user_language": "EN",
            }
        )

        if response.status_code != 201:
            error_detail = response.text
            raise httpx.HTTPStatusError(
                f"GoCardless API error: {error_detail}",
                request=response.request,
                response=response
            )

        data = response.json()
        return {
            "requisition_id": data["id"],
            "link": data["link"],
            "reference": reference
        }


    async def get_requisition_details(self, requisition_id: str) -> dict:
        """Get full requisition details including status and link"""
        token = await self.get_token()
        response = await self.client.get(
            f"/api/v2/requisitions/{requisition_id}/",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_balance_from_accounts(self, account_ids: List[str]) -> List[dict]:
        """Get balance information for given bank account IDs with rate limit handling"""
        token = await self.get_token()
        balances = []
        for account_id in account_ids:
            try:
                response = await self.client.get(
                    f"/api/v2/accounts/{account_id}/balances/",
                    headers={
                        "Authorization": f"Bearer {token}",
                    },
                )
                response.raise_for_status()
                data = response.json()
                # Extract rate limit info from headers
                rate_limit_reset = int(
                    response.headers.get("http_x_ratelimit_account_success_reset", 0)
                    )
                rate_limit_remaining = int(
                    response.headers.get("http_x_ratelimit_account_success_remaining", 0)
                    )
                #return all balance information including account_id
                data["account_id"] = account_id
                data["rate_limit_reset_seconds"] = rate_limit_reset
                data["rate_limit_remaining"] = rate_limit_remaining

                balances.append(data)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Account {account_id} not found (404) - skipping")
                elif e.response.status_code == 429:
                    # Rate limited - check Retry-After header
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after:
                        wait_seconds = int(retry_after)
                        wait_minutes = wait_seconds / 60
                        if wait_minutes >= 60:
                            wait_hours = wait_minutes / 60
                            message = f"Rate limit exceeded. Please try again in {wait_hours:.1f} hours."
                        else:
                            message = f"Rate limit exceeded. Please try again in {wait_minutes:.0f} minutes."
                        logger.error(f"Rate limited (429). Retry after {wait_seconds} seconds")
                    else:
                        message = "Rate limit exceeded. Please try again in 1 hour."
                        logger.error(f"Rate limited (429). No Retry-After header, assuming 1 hour")

                    # Create a more user-friendly error
                    from httpx import HTTPStatusError
                    raise HTTPStatusError(
                        message,
                        request=e.request,
                        response=e.response
                    )
                else:
                    logger.error(f"Error fetching balance for account {account_id}: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error fetching balance for account {account_id}: {e}")
                raise

        return balances
