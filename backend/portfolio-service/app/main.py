import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.logging import setup_logging

setup_logging(level="DEBUG")

load_dotenv()

app = FastAPI(
    title="Portfolio & Net Worth Service",
    description="Portfolio management, banking data, and net worth tracking service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Portfolio & Net Worth Service", "service": "portfolio-service"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "portfolio-service", "environment": "production"}

@app.get("/portfolio")
def get_portfolio():
    return {"message": "Portfolio data endpoint - to be implemented"}

@app.get("/networth")
def get_net_worth():
    return {"message": "Net worth calculation endpoint - to be implemented"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8002, reload=True)