"""Orchestrate a full analysis: fetch -> metrics -> predict -> advise."""

from __future__ import annotations

from app.brain.analyzer import generate_advice, predict_price
from app.metrics.calculator import compute_metrics
from app.schemas.models import AnalysisResponse, RawFinancials
from app.services.financial_data import fetch_financials


def analyze_raw(raw: RawFinancials) -> AnalysisResponse:
    """Run the analysis pipeline over already-fetched fundamentals.

    Split out from :func:`analyze_ticker` so the pure computation can be
    exercised without any network access.
    """

    metrics = compute_metrics(raw)
    prediction = predict_price(raw, metrics)
    advice = generate_advice(raw, metrics, prediction)
    return AnalysisResponse(
        raw=raw,
        metrics=metrics,
        prediction=prediction,
        advice=advice,
    )


def analyze_ticker(ticker: str) -> AnalysisResponse:
    """Fetch fundamentals for ``ticker`` and run the full analysis."""

    raw = fetch_financials(ticker)
    return analyze_raw(raw)
