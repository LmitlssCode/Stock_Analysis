"""The "brain": turn scored metrics into projections and investment advice.

This module is intentionally rule-based and explainable rather than a black
box. The goal is a defensible, transparent narrative: a fundamentals-driven
expected return, blended toward analyst consensus when available, projected
across several investment horizons, plus a plain recommendation with explicit
strengths and risks.

Nothing here is investment advice in the regulated sense; it is an automated
opinion derived from public fundamentals.
"""

from __future__ import annotations

from app.schemas.models import (
    FinancialMetrics,
    InvestmentAdvice,
    PricePrediction,
    Recommendation,
)

# Selectable horizons, in months, with the labels the UI shows.
HORIZONS: list[tuple[int, str]] = [
    (3, "3M"),
    (6, "6M"),
    (12, "1Y"),
    (36, "3Y"),
    (60, "5Y"),
]

# The headline/default horizon used for the recommendation and back-compat.
DEFAULT_HORIZON_MONTHS = 12


def _annualized(price: float, target: float, horizon_months: int) -> float:
    """Compound an annual move implied by a 12-month ``target`` to ``horizon``."""

    annual_return = target / price - 1
    return price * (1 + annual_return) ** (horizon_months / 12)


def predict_price(
    raw,
    metrics: FinancialMetrics,
    horizon_months: int = DEFAULT_HORIZON_MONTHS,
    horizon_label: str = "1Y",
) -> PricePrediction:
    """Estimate a price target at ``horizon_months``.

    The fundamentals score maps to an expected *annual* return in roughly the
    [-25%, +30%] band, nudged by revenue growth, then compounded to the chosen
    horizon. When an analyst consensus target (a ~12-month figure) is available
    we blend toward its annualized path, since it encodes information our
    fundamentals snapshot does not. Confidence decays with longer horizons.
    """

    price = raw.price
    if price is None or price <= 0:
        return PricePrediction(
            current_price=price,
            predicted_price=None,
            expected_return_pct=None,
            horizon_months=horizon_months,
            horizon_label=horizon_label,
            confidence=0.1,
            rationale="No current price available; cannot project a target.",
        )

    # Health score 0-100 -> expected annual return centered at the 50 midpoint.
    health = metrics.health_score
    base_return = (health - 50) / 50 * 0.30  # +/-30% at the extremes

    growth = raw.revenue_growth or 0.0
    growth_tilt = max(-0.10, min(0.10, growth * 0.3))
    annual_return = base_return + growth_tilt

    years = horizon_months / 12
    fundamental_target = price * (1 + annual_return) ** years

    rationale_parts = [
        f"Fundamentals health score of {health:.0f}/100 implies a "
        f"{annual_return:+.1%} annual move, compounded over {horizon_label}."
    ]

    predicted = fundamental_target
    if raw.target_mean_price and raw.target_mean_price > 0:
        # Blend 60% fundamentals / 40% analyst consensus (annualized to horizon).
        analyst_target = _annualized(price, raw.target_mean_price, horizon_months)
        predicted = 0.6 * fundamental_target + 0.4 * analyst_target
        rationale_parts.append(
            f"Blended 40% toward analysts' {raw.target_mean_price:.2f} "
            "12-month consensus target."
        )

    expected_return = (predicted - price) / price

    # Confidence: stronger conviction at score extremes, plus an analyst boost,
    # decaying as the horizon lengthens (the future is harder to see).
    confidence = 0.35 + (abs(health - 50) / 50) * 0.25
    if raw.target_mean_price and raw.target_mean_price > 0:
        confidence += 0.15
    confidence /= 1 + 0.15 * max(0.0, years - 1)
    confidence = round(max(0.1, min(0.85, confidence)), 2)

    return PricePrediction(
        current_price=round(price, 2),
        predicted_price=round(predicted, 2),
        expected_return_pct=round(expected_return * 100, 2),
        horizon_months=horizon_months,
        horizon_label=horizon_label,
        confidence=confidence,
        rationale=" ".join(rationale_parts),
    )


def predict_all_horizons(raw, metrics: FinancialMetrics) -> list[PricePrediction]:
    """Project a price target for every selectable horizon."""

    return [
        predict_price(raw, metrics, months, label) for months, label in HORIZONS
    ]


def _recommendation_from(health: float, expected_return_pct: float | None) -> Recommendation:
    ret = expected_return_pct if expected_return_pct is not None else 0.0
    # Combine "is it a good company" (health) with "is there upside" (return).
    if health >= 70 and ret >= 12:
        return Recommendation.STRONG_BUY
    if health >= 55 and ret >= 5:
        return Recommendation.BUY
    if health < 35 and ret <= -10:
        return Recommendation.STRONG_SELL
    if health < 45 and ret < 0:
        return Recommendation.SELL
    return Recommendation.HOLD


def generate_advice(
    raw, metrics: FinancialMetrics, prediction: PricePrediction
) -> InvestmentAdvice:
    """Produce a recommendation with explicit strengths and risks."""

    health = metrics.health_score
    rec = _recommendation_from(health, prediction.expected_return_pct)

    # Surface the best and worst scoring metrics as strengths/risks.
    ranked = sorted(metrics.metrics, key=lambda m: m.score, reverse=True)
    strengths = [m.commentary for m in ranked if m.score >= 65][:3]
    risks = [m.commentary for m in reversed(ranked) if m.score <= 40][:3]

    if not strengths:
        strengths = ["No standout strengths in the current fundamentals."]
    if not risks:
        risks = ["No major fundamental red flags detected."]

    name = raw.name or raw.ticker
    ret = prediction.expected_return_pct
    ret_txt = f"{ret:+.1f}%" if ret is not None else "an uncertain"
    summary = (
        f"{name} scores {health:.0f}/100 on fundamental health. The model "
        f"projects {ret_txt} over the next {prediction.horizon_months} months, "
        f"supporting a {rec.value.replace('_', ' ')} stance."
    )

    return InvestmentAdvice(
        recommendation=rec,
        summary=summary,
        strengths=strengths,
        risks=risks,
    )
