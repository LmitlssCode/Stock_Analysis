# Stock_Analysis

An analyzer that looks at a ticker, pulls a company's financials from
**Yahoo Finance**, analyzes the company's health, projects future price
action, and provides an explainable investment opinion — viewable on a web
dashboard.

## Quick start

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open <http://localhost:8000/> and enter a ticker (e.g. `AAPL`). Outbound
internet access is required since data is fetched live from Yahoo Finance.

The dashboard shows, for any ticker:

- the current price and company info,
- a **financial health** gauge plus a per-metric breakdown — click a metric to
  see *why* it's strong or weak,
- a **5-year price chart** with a horizon selector (3M / 6M / 1Y / 3Y / 5Y) and
  the model's projected target overlaid,
- **analyst consensus** — rating distribution, consensus score, and the
  low/mean/high 12-month price-target range,
- the **financial statements** (income, balance sheet, cash flow) report-to-report
  with year-over-year change and multi-year averages,
- an **investment recommendation** with the top strengths and risks.

## How the analysis runs

1. **Fetch** — `services` pulls the company's fundamentals from Yahoo Finance
   (via `yfinance`) and normalizes them into a provider-agnostic snapshot.
2. **Score** — `metrics` rates each fundamental (profitability, growth,
   liquidity, leverage, valuation) on a transparent 0–100 scale and blends a
   weighted **health score**.
3. **Predict** — `brain` maps the health score to a 12-month expected return,
   blended toward the analyst consensus target when available.
4. **Advise** — `brain` produces a recommendation (strong buy → strong sell)
   with the company's top strengths and risks.

The dashboard calls `GET /analyze/{ticker}` and renders all of the above.

See [`backend/README.md`](backend/README.md) for architecture, the full list
of endpoints, ways to run the analysis without the web UI, and tests.

## Disclaimer

Output is an automated opinion derived from public fundamentals and is **not**
financial advice.
