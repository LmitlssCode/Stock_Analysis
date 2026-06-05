# Stock Analysis — Backend

A FastAPI service that pulls a company's fundamentals for a given ticker,
scores its financial health, projects 12-month price action, and produces an
explainable investment opinion.

## Architecture

```
app/
  schemas/    Pydantic models — the request/response contract
  services/   Data fetching (yfinance) + pipeline orchestration
  metrics/    Scores each fundamental 0-100 and blends a health score
  brain/      Health-aware price prediction + investment advice
  api/        FastAPI routes
  main.py     ASGI app entrypoint
tests/        Unit + API tests (no network — uses synthetic fixtures)
```

Data flows one way: `services.fetch_financials` produces a provider-agnostic
`RawFinancials`, which `metrics.compute_metrics` scores, which the `brain`
turns into a `PricePrediction` and `InvestmentAdvice`.

## Setup

```bash
cd backend
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Then:

- `GET /analyze/AAPL` — full analysis for a ticker
- `GET /health` — liveness probe
- `GET /docs` — interactive OpenAPI docs

## Test

```bash
cd backend
python -m pytest
```

Tests stub the data provider, so the suite runs offline and deterministically.

## Disclaimer

Output is an automated opinion derived from public fundamentals and is **not**
financial advice.
