"""FastAPI application entrypoint.

Run locally with::

    uvicorn app.main:app --reload --port 8000

Then open the dashboard at http://localhost:8000/
or hit the API directly: GET http://localhost:8000/analyze/AAPL
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Stock Analysis API",
    description=(
        "Pulls a company's fundamentals, scores its financial health, projects "
        "future price action, and produces an explainable investment opinion."
    ),
    version="0.1.0",
)

app.include_router(router)

# Serve the dashboard's static assets (CSS/JS) under /static.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the single-page dashboard."""

    return FileResponse(STATIC_DIR / "index.html")
