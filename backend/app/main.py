"""FastAPI application entrypoint.

Run locally with::

    uvicorn app.main:app --reload --port 8000

Then GET http://localhost:8000/analyze/AAPL
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Stock Analysis API",
    description=(
        "Pulls a company's fundamentals, scores its financial health, projects "
        "future price action, and produces an explainable investment opinion."
    ),
    version="0.1.0",
)

app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "Stock Analysis API",
        "docs": "/docs",
        "example": "/analyze/AAPL",
    }
