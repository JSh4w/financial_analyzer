from fastapi import APIRouter, Request
from app.services.gocardless import GoCardlessClient
# routes/banking.py
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


@banking_router.get("/institutions")
async def list_institutions(request: Request):
    client: GoCardlessClient = request.app.state.banking_client
    institutions = await client.get_institutions()
    # Return the complete list of institutions as provided by the client
    return {"institutions": institutions}

@banking_router.post("/requisition")
async def requisition(request: Request, redirect_uri: str, institution_id: str):
    client: GoCardlessClient = request.app.state.banking_client
    url = await client.create_requisition(redirect_uri, institution_id)
    return {"url": url}
# @router.get("/balance")
# async def get_balance(request: Request):
#     client = request.app.state.gocardless
#     balance = await client.get_balance(account_id)
    # return {"balance": balance}