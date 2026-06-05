"""Turn raw fundamentals into scored, human-readable metrics.

The scoring philosophy here is deliberately simple and transparent: each
metric is mapped onto a 0-100 score via piecewise-linear thresholds, then the
scores are blended with fixed weights into an overall health score. This is
not a trading model — it is an explainable summary of fundamental health.

Every metric carries both a short ``commentary`` (one line) and a longer
``explanation`` describing *why* the score landed where it did and what would
make the metric strong vs. weak.
"""

from __future__ import annotations

from typing import Optional

from app.schemas.models import FinancialMetrics, MetricRating, ScoredMetric


def _rating_from_score(score: float) -> MetricRating:
    if score >= 80:
        return MetricRating.STRONG
    if score >= 65:
        return MetricRating.HEALTHY
    if score >= 45:
        return MetricRating.NEUTRAL
    if score >= 25:
        return MetricRating.WEAK
    return MetricRating.POOR


def _interpolate(value: float, points: list[tuple[float, float]]) -> float:
    """Piecewise-linear map from ``value`` to a score.

    ``points`` is an ascending list of ``(threshold, score)`` pairs. Values
    below the first/above the last threshold clamp to the endpoint score.
    """

    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= value <= x1:
            ratio = (value - x0) / (x1 - x0) if x1 != x0 else 0.0
            return y0 + ratio * (y1 - y0)
    return points[-1][1]  # pragma: no cover - unreachable given clamps above


def _score_lower_better(value: float, points: list[tuple[float, float]]) -> float:
    """Like :func:`_interpolate` but for metrics where lower is better."""

    return _interpolate(value, points)


def _scored(
    name: str,
    value: Optional[float],
    score: Optional[float],
    commentary: str,
    explanation: str = "",
) -> ScoredMetric:
    # A missing input is treated as a neutral 50 so it neither helps nor
    # punishes the company, but the commentary makes the gap explicit.
    if value is None or score is None:
        return ScoredMetric(
            name=name,
            value=value,
            score=50.0,
            rating=MetricRating.NEUTRAL,
            commentary=f"{name}: data unavailable.",
            explanation=(
                f"The data provider did not return a value for {name}, so it is "
                "scored as neutral (50) and neither helps nor hurts the overall "
                "health score."
            ),
        )
    score = max(0.0, min(100.0, score))
    return ScoredMetric(
        name=name,
        value=value,
        score=score,
        rating=_rating_from_score(score),
        commentary=commentary,
        explanation=explanation,
    )


# Weight of each metric in the blended health score. Profitability and the
# balance sheet matter most for "is this a healthy company".
_WEIGHTS: dict[str, float] = {
    "Profit Margin": 1.5,
    "Return on Equity": 1.5,
    "Revenue Growth": 1.2,
    "Earnings Growth": 1.0,
    "Current Ratio": 1.2,
    "Debt to Equity": 1.3,
    "Free Cash Flow": 1.0,
    "Valuation (P/E)": 0.8,
}


def compute_metrics(raw) -> FinancialMetrics:
    """Compute scored metrics and the blended health score from raw data.

    ``raw`` is an :class:`~app.schemas.models.RawFinancials` instance.
    """

    metrics: list[ScoredMetric] = []

    # --- Profitability -------------------------------------------------
    pm = raw.profit_margin
    metrics.append(
        _scored(
            "Profit Margin",
            pm,
            None if pm is None else _interpolate(pm, [(-0.1, 0), (0, 30), (0.1, 60), (0.2, 85), (0.35, 100)]),
            None if pm is None else f"Net margin of {pm:.1%}.",
            None
            if pm is None
            else (
                f"Net profit margin is the share of revenue left as profit after all "
                f"costs. This company keeps {pm:.1%} of every sales dollar. "
                "Above ~20% is considered strong (pricing power, efficiency); "
                "0-10% is thin; below 0% means it is losing money."
            ),
        )
    )

    roe = raw.return_on_equity
    metrics.append(
        _scored(
            "Return on Equity",
            roe,
            None if roe is None else _interpolate(roe, [(-0.05, 0), (0.05, 40), (0.15, 70), (0.25, 90), (0.4, 100)]),
            None if roe is None else f"ROE of {roe:.1%}.",
            None
            if roe is None
            else (
                f"Return on equity measures how much profit the company generates per "
                f"dollar of shareholder equity — here {roe:.1%}. Above ~20% is strong; "
                "5-15% is average; negative means it is destroying shareholder capital."
            ),
        )
    )

    # --- Growth --------------------------------------------------------
    rg = raw.revenue_growth
    metrics.append(
        _scored(
            "Revenue Growth",
            rg,
            None if rg is None else _interpolate(rg, [(-0.1, 0), (0, 40), (0.1, 70), (0.25, 90), (0.5, 100)]),
            None if rg is None else f"Revenue growth of {rg:.1%} YoY.",
            None
            if rg is None
            else (
                f"Year-over-year revenue growth of {rg:.1%}. Above ~15% signals a "
                "fast-expanding business; 0-10% is mature/steady; negative means the "
                "top line is shrinking."
            ),
        )
    )

    eg = raw.earnings_growth
    metrics.append(
        _scored(
            "Earnings Growth",
            eg,
            None if eg is None else _interpolate(eg, [(-0.2, 0), (0, 40), (0.15, 70), (0.3, 90), (0.6, 100)]),
            None if eg is None else f"Earnings growth of {eg:.1%} YoY.",
            None
            if eg is None
            else (
                f"Year-over-year earnings growth of {eg:.1%}. Profits growing faster "
                "than ~15% is strong; flat-to-modest is neutral; falling earnings are "
                "a warning sign even when revenue holds up."
            ),
        )
    )

    # --- Liquidity & leverage -----------------------------------------
    cr = raw.current_ratio
    metrics.append(
        _scored(
            "Current Ratio",
            cr,
            None if cr is None else _interpolate(cr, [(0.5, 0), (1.0, 45), (1.5, 75), (2.0, 95), (3.0, 100)]),
            None if cr is None else f"Current ratio of {cr:.2f}.",
            None
            if cr is None
            else (
                f"Current ratio = current assets / current liabilities = {cr:.2f}. "
                "Above ~1.5 means the company can comfortably cover near-term bills; "
                "below 1.0 means short-term obligations exceed liquid assets, a "
                "liquidity risk."
            ),
        )
    )

    de = raw.debt_to_equity
    # yfinance reports debt-to-equity as a percentage (e.g. 150 == 1.5x).
    de_ratio = None if de is None else (de / 100 if de > 5 else de)
    metrics.append(
        _scored(
            "Debt to Equity",
            de_ratio,
            None if de_ratio is None else _score_lower_better(de_ratio, [(0.0, 100), (0.5, 85), (1.0, 65), (2.0, 35), (4.0, 0)]),
            None if de_ratio is None else f"Debt-to-equity of {de_ratio:.2f}x.",
            None
            if de_ratio is None
            else (
                f"Debt-to-equity of {de_ratio:.2f}x compares borrowings to shareholder "
                "equity (lower is safer). Under ~0.5x is conservative; around 1x is "
                "moderate; above ~2x is heavily leveraged and riskier if earnings dip."
            ),
        )
    )

    fcf = raw.free_cashflow
    metrics.append(
        _scored(
            "Free Cash Flow",
            fcf,
            None if fcf is None else (75.0 if fcf > 0 else 20.0),
            None
            if fcf is None
            else ("Generates positive free cash flow." if fcf > 0 else "Burning cash (negative FCF)."),
            None
            if fcf is None
            else (
                "Free cash flow is the cash left after operating costs and capital "
                "spending — the cash truly available to repay debt, buy back stock, or "
                "pay dividends. "
                + (
                    "This company generates positive free cash flow, a sign of "
                    "self-funding strength."
                    if fcf > 0
                    else "This company is burning cash (negative free cash flow), so it "
                    "may need outside financing to sustain itself."
                )
            ),
        )
    )

    # --- Valuation -----------------------------------------------------
    pe = raw.trailing_pe if raw.trailing_pe is not None else raw.forward_pe
    if pe is not None and pe <= 0:
        # Negative P/E means no earnings; valuation is not meaningful.
        metrics.append(
            _scored(
                "Valuation (P/E)",
                pe,
                30.0,
                "No positive earnings (negative P/E).",
                "A negative price-to-earnings ratio means the company has no positive "
                "earnings to value against, so the shares cannot be assessed on "
                "conventional earnings multiples — treated as a weak valuation signal.",
            )
        )
    else:
        metrics.append(
            _scored(
                "Valuation (P/E)",
                pe,
                None if pe is None else _score_lower_better(pe, [(8, 100), (15, 80), (25, 55), (40, 30), (70, 5)]),
                None if pe is None else f"Trades at a P/E of {pe:.1f}.",
                None
                if pe is None
                else (
                    f"Price-to-earnings of {pe:.1f} is what investors pay per dollar of "
                    "annual earnings (lower is cheaper). Under ~15x is inexpensive; "
                    "15-25x is typical; above ~40x prices in heavy growth expectations "
                    "and leaves little margin for disappointment. A low multiple lifts "
                    "this score but can also signal the market's doubts."
                ),
            )
        )

    # --- Blend ---------------------------------------------------------
    weighted_sum = 0.0
    weight_total = 0.0
    for m in metrics:
        w = _WEIGHTS.get(m.name, 1.0)
        weighted_sum += m.score * w
        weight_total += w
    health_score = round(weighted_sum / weight_total, 1) if weight_total else 50.0

    return FinancialMetrics(
        metrics=metrics,
        health_score=health_score,
        health_rating=_rating_from_score(health_score),
    )
