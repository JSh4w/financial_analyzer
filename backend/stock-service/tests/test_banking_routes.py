"""Tests for /banking routes with a fake GoCardless client and database."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.auth import get_current_user_id
from app.dependencies import get_banking_client, get_supabase_db
from app.main import app
from fastapi.testclient import TestClient


def http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://gc.test")
    return httpx.HTTPStatusError(
        f"HTTP {status}", request=request, response=httpx.Response(status, request=request)
    )


LINKED = {
    "id": "req-ok",
    "status": "LN",
    "institution_id": "GOOD_BANK",
    "accounts": ["acc-1"],
}


@pytest.fixture
def gc():
    client = MagicMock()
    client.get_institution_name = AsyncMock(return_value="Good Bank")
    client.get_requisition_details = AsyncMock(return_value=LINKED)
    client.get_balance_from_accounts = AsyncMock(
        side_effect=lambda ids: [
            {"account_id": i, "balances": [{"amount": "10.00"}]} for i in ids
        ]
    )
    client.create_end_user_agreement = AsyncMock(return_value={"id": "agr-1"})
    client.create_requisition = AsyncMock(
        return_value={"requisition_id": "req-new", "link": "https://bank", "reference": "ref"}
    )
    return client


@pytest.fixture
def db():
    db = MagicMock()
    db.get_user_requisitions.return_value = [
        {"requisition_id": "req-ok", "institution_id": "GOOD_BANK"}
    ]
    db.get_balance_details_for_account.return_value = None
    db.can_refresh_balance.return_value = True
    return db


@pytest.fixture
def api(gc, db):
    async def fake_user():
        return "user-1"

    app.dependency_overrides[get_current_user_id] = fake_user
    app.dependency_overrides[get_banking_client] = lambda: gc
    app.dependency_overrides[get_supabase_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_removed_endpoints_are_gone(api):
    assert api.get("/banking/get_token").status_code in (404, 405)
    assert api.post("/banking/link").status_code in (404, 405)


def test_requisition_creates_fresh_agreement_each_time(api, gc, db):
    for _ in range(2):
        r = api.post(
            "/banking/requisition",
            params={"redirect_uri": "https://app/cb", "institution_id": "GOOD_BANK"},
        )
        assert r.status_code == 200

    assert gc.create_end_user_agreement.await_count == 2
    gc.create_requisition.assert_awaited_with(
        "https://app/cb", "GOOD_BANK", "agr-1", "user-1"
    )


def test_all_balances_happy_path(api):
    r = api.get("/banking/all_balances")
    assert r.status_code == 200
    assert r.json()["balances"] == {"Good Bank": [{"amount": "10.00"}]}


def test_all_balances_survives_one_broken_requisition(api, gc, db):
    db.get_user_requisitions.return_value = [
        {"requisition_id": "req-ok", "institution_id": "GOOD_BANK"},
        {"requisition_id": "req-bad", "institution_id": "BAD_BANK"},
    ]

    async def details(req_id):
        if req_id == "req-bad":
            raise http_error(500)
        return LINKED

    gc.get_requisition_details.side_effect = details

    r = api.get("/banking/all_balances")
    assert r.status_code == 200
    body = r.json()
    assert body["balances"] == {"Good Bank": [{"amount": "10.00"}]}
    assert [p["status"] for p in body["pending_requisitions"]] == ["ERROR"]
    assert body["pending_requisitions"][0]["requisition_id"] == "req-bad"


def test_all_balances_drops_requisition_deleted_at_gocardless(api, gc, db):
    db.get_user_requisitions.return_value = [
        {"requisition_id": "req-gone", "institution_id": "OLD_BANK"}
    ]
    gc.get_requisition_details.side_effect = http_error(404)

    r = api.get("/banking/all_balances")
    assert r.status_code == 200
    assert r.json() == {"balances": {}, "pending_requisitions": []}
    db.delete_requisition.assert_called_once_with("req-gone")


def test_all_balances_falls_back_to_cache_when_rate_limited(api, gc, db):
    gc.get_balance_from_accounts.side_effect = http_error(429)
    db.get_balance_details_for_account.return_value = {
        "balances": [{"amount": "5.00"}]
    }

    r = api.get("/banking/all_balances")
    assert r.status_code == 200
    assert r.json()["balances"] == {"Good Bank": [{"amount": "5.00"}]}
