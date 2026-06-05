"""Synthetic ``RawFinancials`` fixtures for tests (no network)."""

from __future__ import annotations

from app.schemas.models import RawFinancials


def healthy_company(**overrides) -> RawFinancials:
    base = dict(
        ticker="GOOD",
        name="Good Company Inc.",
        sector="Technology",
        currency="USD",
        price=100.0,
        market_cap=500_000_000_000,
        trailing_pe=18.0,
        forward_pe=16.0,
        price_to_book=5.0,
        profit_margin=0.25,
        gross_margin=0.55,
        return_on_equity=0.30,
        revenue_growth=0.20,
        earnings_growth=0.25,
        total_cash=80_000_000_000,
        total_debt=20_000_000_000,
        free_cashflow=40_000_000_000,
        current_ratio=2.2,
        debt_to_equity=30.0,  # yfinance-style percentage -> 0.3x
        target_mean_price=120.0,
    )
    base.update(overrides)
    return RawFinancials(**base)


def weak_company(**overrides) -> RawFinancials:
    base = dict(
        ticker="WEAK",
        name="Weak Company Inc.",
        sector="Industrials",
        currency="USD",
        price=50.0,
        market_cap=2_000_000_000,
        trailing_pe=60.0,
        forward_pe=55.0,
        price_to_book=8.0,
        profit_margin=-0.05,
        gross_margin=0.15,
        return_on_equity=-0.10,
        revenue_growth=-0.08,
        earnings_growth=-0.30,
        total_cash=200_000_000,
        total_debt=3_000_000_000,
        free_cashflow=-150_000_000,
        current_ratio=0.8,
        debt_to_equity=350.0,  # 3.5x
        target_mean_price=45.0,
    )
    base.update(overrides)
    return RawFinancials(**base)
