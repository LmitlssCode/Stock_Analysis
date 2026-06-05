"""Tests for the pure market-data parsers (no network)."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from app.services.market_data import (
    INCOME_ROWS,
    build_analyst,
    build_price_history,
    build_statement,
)


def _income_frame():
    cols = [datetime(2025, 9, 30), datetime(2024, 9, 30), datetime(2023, 9, 30)]
    data = {
        cols[0]: {"Total Revenue": 400.0, "Net Income": 100.0, "Diluted EPS": 7.0},
        cols[1]: {"Total Revenue": 380.0, "Net Income": 90.0, "Diluted EPS": 6.0},
        cols[2]: {"Total Revenue": 360.0, "Net Income": 80.0, "Diluted EPS": 5.0},
    }
    return pd.DataFrame(data)


def test_build_statement_periods_and_yoy_and_avg():
    stmt = build_statement(_income_frame(), "Income Statement", INCOME_ROWS)
    assert stmt is not None
    assert stmt.periods == ["2025-09-30", "2024-09-30", "2023-09-30"]

    rev = next(i for i in stmt.items if i.label == "Revenue")
    assert rev.values == [400.0, 380.0, 360.0]
    # YoY = (400-380)/380 * 100 = 5.3%
    assert rev.yoy_pct == 5.3
    assert rev.avg == 380.0  # (400+380+360)/3


def test_build_statement_skips_missing_rows():
    stmt = build_statement(_income_frame(), "Income Statement", INCOME_ROWS)
    labels = {i.label for i in stmt.items}
    # Gross Profit / Operating Income absent from the frame -> not included.
    assert "Gross Profit" not in labels
    assert {"Revenue", "Net Income", "Diluted EPS"} <= labels


def test_build_statement_empty_returns_none():
    assert build_statement(pd.DataFrame(), "X", INCOME_ROWS) is None
    assert build_statement(None, "X", INCOME_ROWS) is None


def test_build_price_history_filters_nan():
    idx = pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"])
    df = pd.DataFrame({"Close": [10.0, float("nan"), 12.0]}, index=idx)
    points = build_price_history(df)
    assert [p.date for p in points] == ["2024-01-01", "2024-03-01"]
    assert [p.close for p in points] == [10.0, 12.0]


def test_build_analyst_from_info_and_recommendations():
    info = {
        "numberOfAnalystOpinions": 30,
        "recommendationKey": "buy",
        "recommendationMean": 2.0,
    }
    recs = pd.DataFrame([
        {"period": "0m", "strongBuy": 5, "buy": 10, "hold": 8, "sell": 1, "strongSell": 0},
    ])
    targets = {"current": 100.0, "low": 80.0, "mean": 120.0, "median": 118.0, "high": 160.0}

    a = build_analyst(info, recs, targets)
    assert a.num_analysts == 30
    assert a.recommendation_key == "buy"
    assert a.target_mean == 120.0 and a.target_high == 160.0
    assert len(a.ratings) == 1
    assert a.ratings[0].strong_buy == 5 and a.ratings[0].hold == 8
