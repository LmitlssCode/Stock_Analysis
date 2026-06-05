# Stock Analysis — Backend

A FastAPI service that pulls a company's fundamentals for a given ticker,
scores its financial health, projects 12-month price action, and produces an
explainable investment opinion.

## Architecture

```
app/
  schemas/    Pydantic models — the request/response contract
  services/   Data fetching (Yahoo Finance via yfinance) + pipeline orchestration
  metrics/    Scores each fundamental 0-100 and blends a health score
  brain/      Health-aware price prediction + investment advice
  api/        FastAPI routes
  static/     Single-page dashboard (HTML/CSS/JS, no build step)
  main.py     ASGI app entrypoint — serves both the API and the dashboard
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

Then open the **dashboard** at <http://localhost:8000/> and type a ticker
(e.g. `AAPL`). The data comes from Yahoo Finance, so the machine running the
server needs outbound internet access.

Other endpoints:

- `GET /` — interactive dashboard
- `GET /analyze/{ticker}` — full analysis as JSON (e.g. `/analyze/AAPL`)
- `GET /health` — liveness probe
- `GET /docs` — interactive OpenAPI docs

### Without the web UI

You can also run an analysis straight from Python:

```bash
cd backend
python -c "from app.services.analysis import analyze_ticker; \
print(analyze_ticker('AAPL').model_dump_json(indent=2))"
```

or against the running server:

```bash
curl http://localhost:8000/analyze/AAPL
```

## Test

```bash
cd backend
python -m pytest
```

Tests stub the data provider, so the suite runs offline and deterministically.

## Disclaimer

Output is an automated opinion derived from public fundamentals and is **not**
financial advice.
