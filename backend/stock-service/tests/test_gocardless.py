"""Tests for the GoCardless client using an in-memory httpx transport."""

import json
from datetime import datetime, timedelta

import httpx
import pytest

from app.services.gocardless import GoCardlessClient


class FakeGoCardless:
    """Records requests and serves canned GoCardless responses."""

    def __init__(self):
        self.calls: list[tuple[str, str, dict]] = []
        self.refresh_status = 200
        self.token_counter = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else {}
        self.calls.append((request.method, request.url.path, body))
        path = request.url.path

        if path == "/api/v2/token/new/":
            self.token_counter += 1
            return httpx.Response(
                200,
                json={
                    "access": f"access-{self.token_counter}",
                    "access_expires": 86400,
                    "refresh": f"refresh-{self.token_counter}",
                    "refresh_expires": 2592000,
                },
            )
        if path == "/api/v2/token/refresh/":
            if self.refresh_status != 200:
                return httpx.Response(self.refresh_status, json={"detail": "bad"})
            return httpx.Response(
                200, json={"access": "access-refreshed", "access_expires": 86400}
            )
        if path == "/api/v2/agreements/enduser/":
            return httpx.Response(201, json={"id": "agreement-1", **body})
        return httpx.Response(404, json={"detail": "not found"})

    def paths(self) -> list[str]:
        return [p for _, p, _ in self.calls]


@pytest.fixture
def fake():
    return FakeGoCardless()


@pytest.fixture
def client(fake):
    http = httpx.AsyncClient(
        base_url="https://gc.test", transport=httpx.MockTransport(fake.handler)
    )
    return GoCardlessClient("id", "key", http_client=http)


@pytest.mark.asyncio
async def test_first_call_mints_new_token(client, fake):
    assert await client.get_token() == "access-1"
    assert fake.paths() == ["/api/v2/token/new/"]


@pytest.mark.asyncio
async def test_valid_access_token_is_reused(client, fake):
    await client.get_token()
    await client.get_token()
    assert fake.paths() == ["/api/v2/token/new/"]


@pytest.mark.asyncio
async def test_expired_access_token_uses_refresh(client, fake):
    await client.get_token()
    client.access_expires = datetime.now() - timedelta(seconds=1)

    assert await client.get_token() == "access-refreshed"
    assert fake.paths()[-1] == "/api/v2/token/refresh/"


@pytest.mark.asyncio
async def test_expired_refresh_token_mints_new_pair(client, fake):
    await client.get_token()
    client.access_expires = datetime.now() - timedelta(seconds=1)
    client.refresh_expires = datetime.now() - timedelta(seconds=1)

    assert await client.get_token() == "access-2"
    assert "/api/v2/token/refresh/" not in fake.paths()
    assert client.refresh_token == "refresh-2"


@pytest.mark.asyncio
async def test_rejected_refresh_falls_back_to_new_token(client, fake):
    await client.get_token()
    client.access_expires = datetime.now() - timedelta(seconds=1)
    fake.refresh_status = 401

    assert await client.get_token() == "access-2"
    assert fake.paths()[-2:] == ["/api/v2/token/refresh/", "/api/v2/token/new/"]
