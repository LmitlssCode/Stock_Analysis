"use strict";

const els = {
  form: document.getElementById("search"),
  ticker: document.getElementById("ticker"),
  placeholder: document.getElementById("placeholder"),
  loading: document.getElementById("loading"),
  error: document.getElementById("error"),
  result: document.getElementById("result"),
};

const RATING_CLASS = {
  strong: "strong",
  healthy: "healthy",
  neutral: "neutral",
  weak: "weak",
  poor: "poor",
};

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }

function fmtMoney(v, currency) {
  if (v === null || v === undefined) return "—";
  const cur = currency || "USD";
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: cur, maximumFractionDigits: 2 }).format(v);
  } catch {
    return `${v.toFixed(2)} ${cur}`;
  }
}

function fmtPct(v) {
  if (v === null || v === undefined) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}%`;
}

function ratingClass(rating) {
  return RATING_CLASS[rating] || "neutral";
}

async function analyze(ticker) {
  hide(els.placeholder);
  hide(els.result);
  hide(els.error);
  show(els.loading);

  try {
    const resp = await fetch(`/analyze/${encodeURIComponent(ticker)}`);
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${resp.status})`);
    }
    const data = await resp.json();
    render(data);
  } catch (err) {
    hide(els.loading);
    els.error.textContent = err.message || "Something went wrong.";
    show(els.error);
  }
}

function render(data) {
  const { raw, metrics, prediction, advice } = data;

  // Company header
  document.getElementById("company-name").textContent =
    `${raw.name || raw.ticker} (${raw.ticker})`;
  const meta = [raw.sector, raw.industry].filter(Boolean).join(" · ") || "—";
  document.getElementById("company-meta").textContent = meta;
  document.getElementById("price").textContent = fmtMoney(raw.price, raw.currency);

  // Health gauge
  const score = metrics.health_score;
  const rcls = ratingClass(metrics.health_rating);
  const scoreEl = document.getElementById("health-score");
  scoreEl.textContent = Math.round(score);
  scoreEl.className = `ring-score r-${rcls}`;

  const ring = document.getElementById("health-ring");
  const color = getComputedStyle(document.documentElement).getPropertyValue(`--${rcls}`).trim();
  ring.style.background =
    `conic-gradient(${color} ${score * 3.6}deg, var(--panel-2) 0deg)`;
  // inner mask so it reads as a ring
  ring.style.boxShadow = "inset 0 0 0 12px var(--panel)";

  const ratingBadge = document.getElementById("health-rating");
  ratingBadge.textContent = metrics.health_rating;
  ratingBadge.className = `badge r-${rcls}`;

  // Metric bars
  const list = document.getElementById("metrics");
  list.innerHTML = "";
  for (const m of metrics.metrics) {
    const mc = ratingClass(m.rating);
    const li = document.createElement("li");
    li.className = "metric";
    li.innerHTML = `
      <div class="metric-head">
        <span class="metric-name">${m.name}</span>
        <span class="metric-val r-${mc}">${m.rating}</span>
      </div>
      <div class="bar"><div class="bar-fill bg-${mc}" style="width:${m.score}%"></div></div>`;
    li.title = m.commentary;
    list.appendChild(li);
  }

  // Recommendation
  const recEl = document.getElementById("recommendation");
  const recText = advice.recommendation.replace(/_/g, " ");
  recEl.textContent = recText;
  recEl.className = `rec r-${recClass(advice.recommendation)}`;
  document.getElementById("advice-summary").textContent = advice.summary;

  // Prediction
  document.getElementById("predicted-price").textContent = fmtMoney(prediction.predicted_price, raw.currency);
  const retEl = document.getElementById("expected-return");
  retEl.textContent = fmtPct(prediction.expected_return_pct);
  retEl.className = "predict-value " +
    (prediction.expected_return_pct >= 0 ? "r-strong" : "r-poor");
  document.getElementById("confidence").textContent =
    prediction.confidence != null ? `${Math.round(prediction.confidence * 100)}%` : "—";
  document.getElementById("predict-rationale").textContent = prediction.rationale;

  // Strengths & risks
  fillList("strengths", advice.strengths);
  fillList("risks", advice.risks);

  hide(els.loading);
  show(els.result);
}

function recClass(rec) {
  if (rec === "strong_buy" || rec === "buy") return "strong";
  if (rec === "hold") return "neutral";
  return "poor";
}

function fillList(id, items) {
  const ul = document.getElementById(id);
  ul.innerHTML = "";
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    ul.appendChild(li);
  }
}

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const t = els.ticker.value.trim();
  if (t) analyze(t);
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    els.ticker.value = chip.dataset.ticker;
    analyze(chip.dataset.ticker);
  });
});
