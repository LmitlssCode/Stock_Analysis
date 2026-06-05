"""Tests for the prediction + advice brain."""

from __future__ import annotations

from app.brain.analyzer import generate_advice, predict_price
from app.metrics.calculator import compute_metrics
from app.schemas.models import RawFinancials, Recommendation
from tests.factories import healthy_company, weak_company


def _full(raw):
    metrics = compute_metrics(raw)
    prediction = predict_price(raw, metrics)
    advice = generate_advice(raw, metrics, prediction)
    return metrics, prediction, advice


def test_healthy_company_predicts_upside_and_buys():
    _, prediction, advice = _full(healthy_company())
    assert prediction.expected_return_pct is not None
    assert prediction.expected_return_pct > 0
    assert advice.recommendation in (Recommendation.BUY, Recommendation.STRONG_BUY)
    assert advice.strengths


def test_weak_company_predicts_downside_and_sells():
    _, prediction, advice = _full(weak_company())
    assert prediction.expected_return_pct is not None
    assert prediction.expected_return_pct < 0
    assert advice.recommendation in (Recommendation.SELL, Recommendation.STRONG_SELL)
    assert advice.risks


def test_prediction_blends_toward_analyst_target():
    # With a high analyst target, the predicted price should sit between the
    # pure-fundamentals estimate and that target.
    raw = healthy_company(target_mean_price=200.0)
    metrics = compute_metrics(raw)
    pred = predict_price(raw, metrics)
    assert pred.predicted_price is not None
    assert raw.price < pred.predicted_price < 200.0
    assert pred.confidence <= 0.85


def test_missing_price_yields_low_confidence():
    raw = RawFinancials(ticker="NOPRICE")
    metrics = compute_metrics(raw)
    pred = predict_price(raw, metrics)
    assert pred.predicted_price is None
    assert pred.confidence <= 0.2


def test_confidence_is_a_probability():
    for raw in (healthy_company(), weak_company()):
        metrics = compute_metrics(raw)
        pred = predict_price(raw, metrics)
        assert 0.0 <= pred.confidence <= 1.0
