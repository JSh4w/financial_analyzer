# app/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from app.api.endpoints import analysis, data
from app.core.analysis import financial_ratios, technical_indicators
from app.core.data import stock_data
from app.models import database, schemas

# Initialize FastAPI app
app = FastAPI(
    title="Financial Analysis Service",
    description="Python service for financial data analysis",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
app.include_router(data.router, prefix="/data", tags=["Data"])

# Create database tables
database.Base.metadata.create_all(bind=database.engine)

# Dependency to get the database session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "Financial Analysis Service API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/stock/{symbol}/analysis")
def get_stock_analysis(symbol: str, db: Session = Depends(get_db)):
    """
    Get comprehensive analysis for a stock including:
    - Financial ratios
    - Technical indicators
    - Fundamental analysis
    - Growth metrics
    """
    try:
        # Get stock data
        stock_prices = stock_data.get_historical_prices(symbol)
        financial_data = stock_data.get_financial_statements(symbol)
        
        # Perform analysis
        ratios = financial_ratios.calculate_key_ratios(financial_data)
        technical = technical_indicators.calculate_indicators(stock_prices)
        
        # Combine results
        analysis_result = {
            "symbol": symbol,
            "financialRatios": ratios,
            "technicalIndicators": technical,
            "recommendation": generate_recommendation(ratios, technical)
        }
        
        return analysis_result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

def generate_recommendation(ratios, technical):
    """Generate an investment recommendation based on analysis"""

    score = 0
    
    # Example scoring (simplified)
    if ratios.get("pe_ratio", 100) < 15:
        score += 1
    if ratios.get("debt_to_equity", 2) < 1:
        score += 1
    if technical.get("rsi", 50) < 70 and technical.get("rsi", 50) > 30:
        score += 1
    if technical.get("macd_signal", 0) > 0:
        score += 1
        
    # Map score to recommendation
    recommendations = {
        0: "Strong Sell",
        1: "Sell",
        2: "Hold",
        3: "Buy",
        4: "Strong Buy"
    }
    
    return {
        "rating": recommendations.get(score, "Hold"),
        "score": score,
        "maxScore": 4
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=5000, reload=True)