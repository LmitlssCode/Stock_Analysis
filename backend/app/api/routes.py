"""HTTP routes for the stock analysis service."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.models import AnalysisResponse
from app.services.analysis import analyze_ticker
from app.services.financial_data import DataFetchError

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    """Liveness probe."""

    return {"status": "ok"}


@router.get("/analyze/{ticker}", response_model=AnalysisResponse)
def analyze(ticker: str) -> AnalysisResponse:
    """Analyze a single ticker and return health, prediction, and advice."""

    try:
        return analyze_ticker(ticker)
    except DataFetchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
