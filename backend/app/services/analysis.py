"""Orchestrate a full analysis: fetch -> metrics -> predict -> advise."""

from __future__ import annotations

from app.brain.analyzer import (
    DEFAULT_HORIZON_MONTHS,
    generate_advice,
    predict_all_horizons,
    predict_price,
)
from app.metrics.calculator import compute_metrics
from app.schemas.models import AnalysisResponse, RawFinancials
from app.services.financial_data import fetch_financials
from app.services.market_data import fetch_market_extras


def analyze_raw(raw: RawFinancials, extras: dict | None = None) -> AnalysisResponse:
    """Run the analysis pipeline over already-fetched fundamentals.

    Split out from :func:`analyze_ticker` so the pure computation can be
    exercised without any network access. ``extras`` optionally carries the
    price history, statements, and analyst opinions.
    """

    extras = extras or {}
    metrics = compute_metrics(raw)

    predictions = predict_all_horizons(raw, metrics)
    # Headline prediction = default horizon (1Y), reused for the recommendation.
    default = next(
        (p for p in predictions if p.horizon_months == DEFAULT_HORIZON_MONTHS),
        None,
    ) or predict_price(raw, metrics)
    advice = generate_advice(raw, metrics, default)

    return AnalysisResponse(
        raw=raw,
        metrics=metrics,
        prediction=default,
        predictions=predictions,
        advice=advice,
        price_history=extras.get("price_history", []),
        statements=extras.get("statements", []),
        analyst=extras.get("analyst"),
    )


def analyze_ticker(ticker: str) -> AnalysisResponse:
    """Fetch fundamentals + market data for ``ticker`` and run the analysis."""

    raw = fetch_financials(ticker)
    try:
        extras = fetch_market_extras(ticker)
    except Exception:
        # Charts/tables are enrichment; never let them break the core analysis.
        extras = {}
    return analyze_raw(raw, extras)
