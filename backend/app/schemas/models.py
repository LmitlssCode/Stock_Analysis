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
    # A longer, plain-language "why" — what the number means and what would
    # make it strong vs. weak. Surfaced in the UI as an expandable explanation.
    explanation: str = ""


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
    horizon_label: str = ""
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


class PricePoint(BaseModel):
    """A single ``(date, close)`` sample for the price-history chart."""

    date: str
    close: float


class FinancialLineItem(BaseModel):
    """One row of a financial statement across reporting periods.

    ``values`` is aligned to the parent statement's ``periods`` list, newest
    period first. ``yoy_pct`` is the most-recent year-over-year change and
    ``avg`` is the simple average across the available periods (the "5-yr
    average" when five years are present).
    """

    label: str
    unit: str  # e.g. "USD" for absolute figures, "per share" for EPS
    values: list[Optional[float]]
    yoy_pct: Optional[float] = None
    avg: Optional[float] = None


class FinancialStatement(BaseModel):
    """An annual financial statement (income / balance sheet / cash flow)."""

    title: str
    periods: list[str]  # fiscal-year-end dates, newest first
    items: list[FinancialLineItem]


class AnalystRatingPeriod(BaseModel):
    """Analyst rating counts for one snapshot period (e.g. "0m", "-1m")."""

    period: str
    strong_buy: int
    buy: int
    hold: int
    sell: int
    strong_sell: int


class AnalystOpinions(BaseModel):
    """Aggregated sell-side analyst consensus from the data provider."""

    num_analysts: Optional[int] = None
    recommendation_key: Optional[str] = None  # e.g. "buy"
    recommendation_mean: Optional[float] = None  # 1 (strong buy) .. 5 (strong sell)

    current_price: Optional[float] = None
    target_low: Optional[float] = None
    target_mean: Optional[float] = None
    target_median: Optional[float] = None
    target_high: Optional[float] = None

    ratings: list[AnalystRatingPeriod] = []


class AnalysisResponse(BaseModel):
    """Top-level payload returned by the ``/analyze`` endpoint."""

    raw: RawFinancials
    metrics: FinancialMetrics
    # The default-horizon (1Y) prediction, kept for API/back-compat.
    prediction: PricePrediction
    # One projection per selectable horizon (3M, 6M, 1Y, 3Y, 5Y) so the UI can
    # switch horizons instantly without re-fetching.
    predictions: list[PricePrediction] = []
    advice: InvestmentAdvice

    price_history: list[PricePoint] = []
    statements: list[FinancialStatement] = []
    analyst: Optional[AnalystOpinions] = None
