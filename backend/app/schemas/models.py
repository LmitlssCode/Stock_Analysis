"""Pydantic models describing the analysis request/response contract.

These models are the boundary between the internal computation modules
(``services``/``metrics``/``brain``) and the API layer. Every field that
originates from an external provider is optional, because real-world
financial data is frequently incomplete.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RawFinancials(BaseModel):
    """Normalized snapshot of a company's fundamentals.

    Produced by :mod:`app.services.financial_data` from whatever upstream
    provider is in use. Keeping this provider-agnostic means the metrics and
    brain modules never need to know where the numbers came from.
    """

    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    currency: Optional[str] = None

    price: Optional[float] = None
    market_cap: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    beta: Optional[float] = None

    # Valuation
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    price_to_book: Optional[float] = None

    # Profitability
    profit_margin: Optional[float] = None
    gross_margin: Optional[float] = None
    return_on_equity: Optional[float] = None

    # Growth
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None

    # Balance sheet / liquidity
    total_cash: Optional[float] = None
    total_debt: Optional[float] = None
    free_cashflow: Optional[float] = None
    current_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None

    # Analyst consensus (used as a sanity check, not a source of truth)
    target_mean_price: Optional[float] = None


class MetricRating(str, Enum):
    STRONG = "strong"
    HEALTHY = "healthy"
    NEUTRAL = "neutral"
    WEAK = "weak"
    POOR = "poor"


class ScoredMetric(BaseModel):
    """A single fundamental metric scored on a 0-100 scale."""

    name: str
    value: Optional[float] = None
    score: float = Field(ge=0, le=100)
    rating: MetricRating
    commentary: str


class FinancialMetrics(BaseModel):
    """Collection of scored metrics plus a blended health score."""

    metrics: list[ScoredMetric]
    health_score: float = Field(ge=0, le=100)
    health_rating: MetricRating


class PricePrediction(BaseModel):
    current_price: Optional[float] = None
    predicted_price: Optional[float] = None
    expected_return_pct: Optional[float] = None
    horizon_months: int
    confidence: float = Field(ge=0, le=1)
    rationale: str


class Recommendation(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class InvestmentAdvice(BaseModel):
    recommendation: Recommendation
    summary: str
    strengths: list[str]
    risks: list[str]


class AnalysisResponse(BaseModel):
    """Top-level payload returned by the ``/analyze`` endpoint."""

    raw: RawFinancials
    metrics: FinancialMetrics
    prediction: PricePrediction
    advice: InvestmentAdvice
