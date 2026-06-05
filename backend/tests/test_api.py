"""API tests using a stubbed data provider (no network)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.financial_data import DataFetchError
from tests.factories import healthy_company

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_analyze_endpoint_with_stubbed_fetch(monkeypatch):
    monkeypatch.setattr(
        "app.services.analysis.fetch_financials",
        lambda ticker: healthy_company(ticker=ticker.upper()),
    )
    resp = client.get("/analyze/good")
    assert resp.status_code == 200
    body = resp.json()
    assert body["raw"]["ticker"] == "GOOD"
    assert body["metrics"]["health_score"] >= 75
    assert body["advice"]["recommendation"] in ("buy", "strong_buy")


def test_analyze_unknown_ticker_returns_404(monkeypatch):
    def _boom(ticker):
        raise DataFetchError("No data found")

    monkeypatch.setattr("app.services.analysis.fetch_financials", _boom)
    resp = client.get("/analyze/ZZZZ")
    assert resp.status_code == 404
