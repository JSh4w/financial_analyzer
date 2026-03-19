"""DuckDB database management endpoints"""

from logging import getLogger

from app.auth import get_current_user_id
from app.database.stock_data_manager import StockDataManager
from app.dependencies import get_db_manager
from fastapi import APIRouter, Depends, HTTPException

logger = getLogger(__name__)
router = APIRouter(prefix="/database")


@router.get("/stats")
async def get_database_stats(
    db_manager: StockDataManager = Depends(get_db_manager),
    _: str = Depends(get_current_user_id),
):
    """Get database statistics for all symbols"""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database manager not running")

    try:
        stats = db_manager.get_symbols_stats()
        return {
            "stats": [
                {
                    "symbol": row[0],
                    "candle_count": row[1],
                    "first_candle": row[2],
                    "last_candle": row[3],
                    "last_updated": str(row[4]),
                }
                for row in stats
            ],
            "total_symbols": len(stats),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e


@router.get("/export/{symbol}")
async def export_symbol_data(
    symbol: str,
    db_manager: StockDataManager = Depends(get_db_manager),
    _: str = Depends(get_current_user_id),
):
    """Export symbol data to parquet file"""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database manager not running")

    try:
        output_file = db_manager.export_to_parquet(symbol.upper())
        if output_file:
            return {"message": "Data exported successfully", "file": output_file}
        else:
            raise HTTPException(status_code=500, detail="Export failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}") from e


@router.get("/candle_count/{symbol}")
async def get_candle_count(
    symbol: str,
    db_manager: StockDataManager = Depends(get_db_manager),
    _: str = Depends(get_current_user_id),
):
    """Get candle count for a specific symbol"""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database manager not running")

    try:
        count = db_manager.get_candle_count(symbol.upper())
        return {"symbol": symbol.upper(), "candle_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e
