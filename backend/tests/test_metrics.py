"""Tests for the metric scoring calculator."""

from __future__ import annotations

from app.metrics.calculator import compute_metrics
from app.schemas.models import MetricRating, RawFinancials
from tests.factories import healthy_company, weak_company


def test_healthy_company_scores_high():
    metrics = compute_metrics(healthy_company())
    assert metrics.health_score >= 75
    assert metrics.health_rating in (MetricRating.STRONG, MetricRating.HEALTHY)


def test_weak_company_scores_low():
    metrics = compute_metrics(weak_company())
    assert metrics.health_score <= 40
    assert metrics.health_rating in (MetricRating.WEAK, MetricRating.POOR)


def test_health_score_is_bounded():
    for raw in (healthy_company(), weak_company()):
        metrics = compute_metrics(raw)
        assert 0 <= metrics.health_score <= 100
        for m in metrics.metrics:
            assert 0 <= m.score <= 100


def test_missing_data_is_neutral():
    raw = RawFinancials(ticker="EMPTY")
    metrics = compute_metrics(raw)
    # Every metric falls back to a neutral 50 when inputs are absent.
    assert all(m.score == 50.0 for m in metrics.metrics)
    assert metrics.health_score == 50.0


def test_debt_to_equity_percentage_normalization():
    # 150 (percent form) and 1.5 (ratio form) should score identically.
    pct = compute_metrics(RawFinancials(ticker="A", debt_to_equity=150.0))
    ratio = compute_metrics(RawFinancials(ticker="B", debt_to_equity=1.5))
    pct_de = next(m for m in pct.metrics if m.name == "Debt to Equity")
    ratio_de = next(m for m in ratio.metrics if m.name == "Debt to Equity")
    assert pct_de.score == ratio_de.score


def test_negative_pe_is_penalized():
    metrics = compute_metrics(RawFinancials(ticker="LOSS", trailing_pe=-10.0))
    pe = next(m for m in metrics.metrics if m.name == "Valuation (P/E)")
    assert pe.score <= 35
