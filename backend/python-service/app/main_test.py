# backend/python-service/app/main_test.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os 
import websockets
import json 
import asyncio
from datetime import datetime 
#from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


latest_data = {"message": "No data received yet", "timestamp": None}


#Finnhub API keys
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

# What to do to received data 
async def connect_to_finnhub():
    """Handles incoming WebSocket messages from srever"""
    global latest_data
    uri = f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}"
    try:
        async with websockets.connect(uri) as ws:
            await ws.send('{"type":"subscribe","symbol":"AAPL"}')
            print("Subscribed to APPLE")
            try:
                async for message in ws:
                    data = json.loads(message)
                    timestamp = datetime.now().isoformat()

                    #Update data 
                    latest_data = {
                        "message": data,
                        "timestamp": timestamp
                    }
            except json.JSONDecodeError:
                print(f"Failed to parse message {message}")

            # #get and store symbol
            # if 'data' in data:
            #     for trade in data['data']:
            #         symbol = trade.get('s','unknown')
            #         stock_data[symbol] = {
            #             "price": trade.get('p'),
            #             "volume": trade.get('v'),
            #             "timestamp": trade.get('t'),
            #             "conditions": trade.get('c',[]),
            #             "last_updated": timestamp
            #         }
            # print(f"Received data: {data}")
    except Exception as e :
        print(f"Failed to parse message: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(connect_to_finnhub())
    yield 

# Import your actual app creation logic, but configure it for testing
app = FastAPI(
    title="Financial Analysis Service",
    description="Python service for financial data analysis",
    version="0.0.1",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Stock service"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "environment": "production"}

@app.get("/apple")
def get_stock_data():
    return latest_data

# Special test-only endpoints can be added here
@app.get("/test/reset")
def reset_test_data():
    """Endpoint to reset test data between test runs"""
    # You can add logic here to reset any test databases or state
    return {"message": "Test data reset successfully"}


# This allows running the file directly for testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main_test:app", host="0.0.0.0", port=5000, reload=True)