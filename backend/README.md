# Stock Analysis — Backend

A FastAPI service that pulls a company's fundamentals for a given ticker,
scores its financial health, projects price action across several horizons,
summarizes analyst consensus, surfaces the financial statements, and produces
an explainable investment opinion.

## What the dashboard shows

- **Financial health** — a 0–100 score with a per-metric breakdown; click any
  metric for a plain-language explanation of *why* it's strong or weak.
- **Price & projection** — a 5-year price chart with a horizon selector
  (3M / 6M / 1Y / 3Y / 5Y); the model's target is overlaid and updates instantly.
- **Analyst consensus** — rating distribution (strong buy → strong sell),
  consensus key + mean score + number of analysts, and the low/mean/high
  12-month price-target range.
- **Financial statements** — income statement, balance sheet, and cash flow,
  report-to-report with year-over-year change and a multi-year average.

## Architecture

```
app/
  schemas/    Pydantic models — the request/response contract
  services/   financial_data (fundamentals) + market_data (history, statements,
              analysts) + analysis orchestration, all via Yahoo Finance/yfinance
  metrics/    Scores each fundamental 0-100 (with explanations) + health score
  brain/      Multi-horizon price projection + investment advice
  api/        FastAPI routes
  static/     Single-page dashboard (HTML/CSS/JS + Chart.js CDN, no build step)
  main.py     ASGI app entrypoint — serves both the API and the dashboard
tests/        Unit + API tests (no network — synthetic fixtures & frames)
```

Data flows one way: `services` produces a provider-agnostic `RawFinancials`
(plus price history, statements, and analyst opinions), which
`metrics.compute_metrics` scores, which the `brain` turns into per-horizon
`PricePrediction`s and `InvestmentAdvice`. A single `/analyze/{ticker}` call
returns every horizon so the UI switches between them without re-fetching.

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
