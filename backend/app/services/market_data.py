"""Fetch richer market data: price history, statements, and analyst opinions.

The pure ``build_*`` parsers accept already-fetched structures (pandas frames
and dicts) so they can be unit-tested without the network. ``fetch_market_extras``
does the actual provider calls and degrades gracefully: if any one section
fails, the others are still returned.
"""

from __future__ import annotations

from typing import Optional

from app.schemas.models import (
    AnalystOpinions,
    AnalystRatingPeriod,
    FinancialLineItem,
    FinancialStatement,
    PricePoint,
)

MAX_PERIODS = 5  # show up to five fiscal years ("5-yr average")

# (display label, provider row key, unit) for each statement we surface.
INCOME_ROWS = [
    ("Revenue", "Total Revenue", "USD"),
    ("Gross Profit", "Gross Profit", "USD"),
    ("Operating Income", "Operating Income", "USD"),
    ("Net Income", "Net Income", "USD"),
    ("Diluted EPS", "Diluted EPS", "per share"),
]
BALANCE_ROWS = [
    ("Total Assets", "Total Assets", "USD"),
    ("Total Debt", "Total Debt", "USD"),
    ("Cash & Equivalents", "Cash And Cash Equivalents", "USD"),
    ("Stockholders' Equity", "Stockholders Equity", "USD"),
    ("Total Liabilities", "Total Liabilities Net Minority Interest", "USD"),
]
CASHFLOW_ROWS = [
    ("Operating Cash Flow", "Operating Cash Flow", "USD"),
    ("Capital Expenditure", "Capital Expenditure", "USD"),
    ("Free Cash Flow", "Free Cash Flow", "USD"),
]


def _clean(value) -> Optional[float]:
    """Coerce a provider cell to ``float`` or ``None`` (NaN-safe)."""

    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN check without importing math


def build_statement(df, title: str, row_specs: list[tuple[str, str, str]]) -> Optional[FinancialStatement]:
    """Build a :class:`FinancialStatement` from a yfinance statement frame.

    ``df`` has reporting dates as columns (newest first) and line-item names as
    the index. Returns ``None`` if the frame is empty.
    """

    if df is None or getattr(df, "empty", True):
        return None

    columns = list(df.columns)[:MAX_PERIODS]
    periods = [str(getattr(c, "date", lambda: c)()) for c in columns]

    items: list[FinancialLineItem] = []
    for label, key, unit in row_specs:
        if key not in df.index:
            continue
        values = [_clean(df.loc[key, c]) for c in columns]
        present = [v for v in values if v is not None]
        if not present:
            continue

        yoy_pct = None
        if len(values) >= 2 and values[0] is not None and values[1] not in (None, 0):
            yoy_pct = round((values[0] - values[1]) / abs(values[1]) * 100, 1)
        avg = round(sum(present) / len(present), 4)

        items.append(
            FinancialLineItem(label=label, unit=unit, values=values, yoy_pct=yoy_pct, avg=avg)
        )

    if not items:
        return None
    return FinancialStatement(title=title, periods=periods, items=items)


def build_price_history(history_df) -> list[PricePoint]:
    """Build the price-history series from a yfinance ``history`` frame."""

    if history_df is None or getattr(history_df, "empty", True) or "Close" not in history_df:
        return []
    points: list[PricePoint] = []
    for idx, close in history_df["Close"].items():
        c = _clean(close)
        if c is None:
            continue
        date = str(getattr(idx, "date", lambda: idx)())
        points.append(PricePoint(date=date, close=round(c, 2)))
    return points


def build_analyst(info: dict, recommendations_df, price_targets: Optional[dict]) -> AnalystOpinions:
    """Assemble analyst consensus from info, the recommendations frame, and targets."""

    info = info or {}
    targets = price_targets or {}

    ratings: list[AnalystRatingPeriod] = []
    if recommendations_df is not None and not getattr(recommendations_df, "empty", True):
        for _, row in recommendations_df.iterrows():
            ratings.append(
                AnalystRatingPeriod(
                    period=str(row.get("period", "")),
                    strong_buy=int(row.get("strongBuy", 0) or 0),
                    buy=int(row.get("buy", 0) or 0),
                    hold=int(row.get("hold", 0) or 0),
                    sell=int(row.get("sell", 0) or 0),
                    strong_sell=int(row.get("strongSell", 0) or 0),
                )
            )

    return AnalystOpinions(
        num_analysts=info.get("numberOfAnalystOpinions"),
        recommendation_key=info.get("recommendationKey"),
        recommendation_mean=info.get("recommendationMean"),
        current_price=targets.get("current") or info.get("currentPrice"),
        target_low=targets.get("low") or info.get("targetLowPrice"),
        target_mean=targets.get("mean") or info.get("targetMeanPrice"),
        target_median=targets.get("median") or info.get("targetMedianPrice"),
        target_high=targets.get("high") or info.get("targetHighPrice"),
        ratings=ratings,
    )


def fetch_market_extras(ticker: str) -> dict:
    """Fetch price history, statements, and analyst opinions for ``ticker``.

    Returns a dict with keys ``price_history``, ``statements`` and ``analyst``.
    Each section is fetched independently so a single provider hiccup does not
    sink the whole analysis.
    """

    import yfinance as yf

    t = yf.Ticker(ticker)
    extras: dict = {"price_history": [], "statements": [], "analyst": None}

    try:
        extras["price_history"] = build_price_history(t.history(period="5y", interval="1mo"))
    except Exception:
        pass

    statements: list[FinancialStatement] = []
    for attr, title, rows in (
        ("income_stmt", "Income Statement", INCOME_ROWS),
        ("balance_sheet", "Balance Sheet", BALANCE_ROWS),
        ("cashflow", "Cash Flow", CASHFLOW_ROWS),
    ):
        try:
            stmt = build_statement(getattr(t, attr), title, rows)
            if stmt is not None:
                statements.append(stmt)
        except Exception:
            continue
    extras["statements"] = statements

    try:
        try:
            info = t.info
        except Exception:
            info = {}
        try:
            recs = t.recommendations
        except Exception:
            recs = None
        try:
            targets = t.analyst_price_targets
        except Exception:
            targets = None
        extras["analyst"] = build_analyst(info, recs, targets)
    except Exception:
        pass

    return extras
