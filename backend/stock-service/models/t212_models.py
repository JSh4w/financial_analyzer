"""Pydantic models for Trading212 API responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class T212SummaryResponse(BaseModel):
    """
    Trading212 account summary response formatted for frontend.

    This model transforms the raw Trading212 API response into the format
    expected by the frontend application.
    """

    totalWorth: float = Field(..., description="Total account value")
    totalCash: float = Field(..., description="Total cash in account")
    totalPpl: float = Field(..., description="Total profit/loss")
    totalResult: float = Field(..., description="Total result")
    investedValue: float = Field(..., description="Current value of investments")
    pieCash: float = Field(..., description="Cash in pies")
    blockedForStocks: float = Field(..., description="Cash reserved for orders")
    result: float = Field(..., description="Result value")
    dividend: float = Field(0.0, description="Dividend earnings")
    interest: float = Field(0.0, description="Interest earnings")
    fee: float = Field(0.0, description="Fees paid")
    free: float = Field(..., description="Cash available to trade")

    @classmethod
    def from_t212_api(cls, raw_data: dict) -> T212SummaryResponse:
        """
        Transform raw Trading212 API response to frontend format.

        Args:
            raw_data: Raw response from Trading212 /account/summary endpoint

        Returns:
            Formatted response matching frontend expectations
        """
        cash = raw_data.get("cash", {})
        investments = raw_data.get("investments", {})

        # Calculate total profit/loss (realized + unrealized)
        realized_ppl = investments.get("realizedProfitLoss", 0)
        unrealized_ppl = investments.get("unrealizedProfitLoss", 0)
        total_ppl = realized_ppl + unrealized_ppl

        # Calculate total cash
        available = cash.get("availableToTrade", 0)
        reserved = cash.get("reservedForOrders", 0)
        in_pies = cash.get("inPies", 0)
        total_cash = available + reserved + in_pies

        return cls(
            totalWorth=raw_data.get("totalValue", 0),
            totalCash=total_cash,
            totalPpl=total_ppl,
            totalResult=total_ppl,  # Same as totalPpl
            investedValue=investments.get("currentValue", 0),
            pieCash=in_pies,
            blockedForStocks=reserved,
            result=total_ppl,  # Same as totalPpl
            dividend=0.0,  # Not provided by this endpoint
            interest=0.0,  # Not provided by this endpoint
            fee=0.0,  # Not provided by this endpoint
            free=available,
        )
