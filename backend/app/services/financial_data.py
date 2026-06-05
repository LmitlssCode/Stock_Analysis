"""Fetch and normalize company fundamentals from an external provider.

The default provider is ``yfinance``. It is imported lazily so that the
metrics/brain modules and their tests have no hard dependency on a network
library. Any provider-specific quirks are contained here; everything
downstream consumes the clean :class:`~app.schemas.models.RawFinancials`.
"""

from __future__ import annotations

from app.schemas.models import RawFinancials


class DataFetchError(RuntimeError):
    """Raised when fundamentals for a ticker cannot be retrieved."""


def _get(info: dict, *keys: str):
    """Return the first present, non-null value among ``keys``."""

    for key in keys:
        value = info.get(key)
        if value is not None:
            return value
    return None


def fetch_financials(ticker: str) -> RawFinancials:
    """Fetch and normalize fundamentals for ``ticker``.

    Raises :class:`DataFetchError` if the ticker is unknown or the provider
    returns nothing usable.
    """

    ticker = ticker.strip().upper()
    if not ticker:
        raise DataFetchError("Ticker symbol is required.")

    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise DataFetchError(
            "yfinance is not installed; install backend/requirements.txt."
        ) from exc

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:  # network/provider errors are opaque
        raise DataFetchError(f"Failed to fetch data for {ticker}: {exc}") from exc

    # yfinance returns a near-empty dict for invalid tickers.
    price = _get(info, "currentPrice", "regularMarketPrice", "previousClose")
    if price is None and not info.get("longName") and not info.get("shortName"):
        raise DataFetchError(f"No data found for ticker '{ticker}'.")

    return RawFinancials(
        ticker=ticker,
        name=_get(info, "longName", "shortName"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        currency=info.get("currency"),
        price=price,
        market_cap=info.get("marketCap"),
        fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
        fifty_two_week_low=info.get("fiftyTwoWeekLow"),
        beta=info.get("beta"),
        trailing_pe=info.get("trailingPE"),
        forward_pe=info.get("forwardPE"),
        price_to_book=info.get("priceToBook"),
        profit_margin=_get(info, "profitMargins"),
        gross_margin=_get(info, "grossMargins"),
        return_on_equity=info.get("returnOnEquity"),
        revenue_growth=info.get("revenueGrowth"),
        earnings_growth=_get(info, "earningsGrowth", "earningsQuarterlyGrowth"),
        total_cash=info.get("totalCash"),
        total_debt=info.get("totalDebt"),
        free_cashflow=info.get("freeCashflow"),
        current_ratio=info.get("currentRatio"),
        debt_to_equity=info.get("debtToEquity"),
        target_mean_price=_get(info, "targetMeanPrice"),
    )
