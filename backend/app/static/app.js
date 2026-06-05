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
  strong: "strong", healthy: "healthy", neutral: "neutral", weak: "weak", poor: "poor",
};

// Holds the current analysis so the horizon buttons can re-render without refetching.
let current = null;
let priceChart = null;

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }
function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function fmtMoney(v, currency) {
  if (v === null || v === undefined) return "—";
  const cur = currency || "USD";
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: cur, maximumFractionDigits: 2 }).format(v);
  } catch { return `${v.toFixed(2)} ${cur}`; }
}
function fmtPct(v) {
  if (v === null || v === undefined) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}
function fmtBig(v, unit) {
  if (v === null || v === undefined) return "—";
  if (unit === "per share") return v.toFixed(2);
  const abs = Math.abs(v);
  if (abs >= 1e12) return (v / 1e12).toFixed(2) + "T";
  if (abs >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (abs >= 1e6) return (v / 1e6).toFixed(1) + "M";
  return v.toFixed(0);
}
function ratingClass(rating) { return RATING_CLASS[rating] || "neutral"; }
function recClass(rec) {
  if (rec === "strong_buy" || rec === "buy") return "strong";
  if (rec === "hold") return "neutral";
  return "poor";
}

async function analyze(ticker) {
  hide(els.placeholder); hide(els.result); hide(els.error);
  show(els.loading);
  try {
    const resp = await fetch(`/analyze/${encodeURIComponent(ticker)}`);
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${resp.status})`);
    }
    current = await resp.json();
    render(current);
  } catch (err) {
    hide(els.loading);
    els.error.textContent = err.message || "Something went wrong.";
    show(els.error);
  }
}

function render(data) {
  const { raw, metrics, advice } = data;

  document.getElementById("company-name").textContent = `${raw.name || raw.ticker} (${raw.ticker})`;
  document.getElementById("company-meta").textContent =
    [raw.sector, raw.industry].filter(Boolean).join(" · ") || "—";
  document.getElementById("price").textContent = fmtMoney(raw.price, raw.currency);

  renderHealth(metrics);
  renderHorizons(data);
  renderRecommendation(advice);
  renderAnalyst(data.analyst, raw);
  fillList("strengths", advice.strengths);
  fillList("risks", advice.risks);
  renderStatements(data.statements || []);

  hide(els.loading);
  show(els.result);
}

function renderHealth(metrics) {
  const score = metrics.health_score;
  const rcls = ratingClass(metrics.health_rating);
  const scoreEl = document.getElementById("health-score");
  scoreEl.textContent = Math.round(score);
  scoreEl.className = `ring-score r-${rcls}`;

  const ring = document.getElementById("health-ring");
  ring.style.background = `conic-gradient(${cssVar("--" + rcls)} ${score * 3.6}deg, var(--panel-2) 0deg)`;
  ring.style.boxShadow = "inset 0 0 0 12px var(--panel)";

  const badge = document.getElementById("health-rating");
  badge.textContent = metrics.health_rating;
  badge.className = `badge r-${rcls}`;

  const list = document.getElementById("metrics");
  list.innerHTML = "";
  for (const m of metrics.metrics) {
    const mc = ratingClass(m.rating);
    const li = document.createElement("li");
    li.className = "metric";
    li.innerHTML = `
      <div class="metric-head">
        <span class="metric-name">▸ ${m.name}</span>
        <span class="metric-val r-${mc}">${m.rating} · ${Math.round(m.score)}</span>
      </div>
      <div class="bar"><div class="bar-fill bg-${mc}" style="width:${m.score}%"></div></div>
      <div class="metric-why"><p>${m.explanation || m.commentary}</p></div>`;
    li.querySelector(".metric-head").addEventListener("click", () => {
      li.classList.toggle("open");
      const arrow = li.querySelector(".metric-name");
      arrow.textContent = (li.classList.contains("open") ? "▾ " : "▸ ") + m.name;
    });
    list.appendChild(li);
  }
}

function renderHorizons(data) {
  const preds = data.predictions && data.predictions.length
    ? data.predictions : [data.prediction];
  const wrap = document.getElementById("horizons");
  wrap.innerHTML = "";
  // Default to the 1Y horizon if present.
  let selected = preds.find((p) => p.horizon_months === 12) || preds[0];
  preds.forEach((p) => {
    const btn = document.createElement("button");
    btn.className = "hbtn" + (p === selected ? " active" : "");
    btn.textContent = p.horizon_label || `${p.horizon_months}M`;
    btn.addEventListener("click", () => {
      wrap.querySelectorAll(".hbtn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      showProjection(data, p);
    });
    wrap.appendChild(btn);
  });
  showProjection(data, selected);
}

function showProjection(data, p) {
  document.getElementById("horizon-label").textContent = p.horizon_label || "";
  document.getElementById("predicted-price").textContent = fmtMoney(p.predicted_price, data.raw.currency);
  const retEl = document.getElementById("expected-return");
  retEl.textContent = fmtPct(p.expected_return_pct);
  retEl.className = "predict-value " + ((p.expected_return_pct || 0) >= 0 ? "r-strong" : "r-poor");
  document.getElementById("confidence").textContent =
    p.confidence != null ? `${Math.round(p.confidence * 100)}%` : "—";
  document.getElementById("predict-rationale").textContent = p.rationale || "";
  drawChart(data.price_history || [], p);
}

function drawChart(history, prediction) {
  const canvas = document.getElementById("price-chart");
  const labels = history.map((h) => h.date);
  const closes = history.map((h) => h.close);

  // Build a dashed projection segment from the last close to the target.
  let projData = null;
  if (closes.length && prediction.predicted_price != null) {
    const months = prediction.horizon_months || 12;
    const future = new Date(labels[labels.length - 1]);
    future.setMonth(future.getMonth() + months);
    labels.push(future.toISOString().slice(0, 10));
    projData = new Array(closes.length - 1).fill(null);
    projData.push(closes[closes.length - 1], prediction.predicted_price);
    closes.push(null);
  }

  const up = (prediction.expected_return_pct || 0) >= 0;
  const projColor = up ? cssVar("--strong") : cssVar("--poor");

  const datasets = [{
    label: "Price",
    data: closes,
    borderColor: cssVar("--accent"),
    backgroundColor: "rgba(79,140,255,0.08)",
    borderWidth: 2, pointRadius: 0, tension: 0.25, fill: true, spanGaps: false,
  }];
  if (projData) {
    datasets.push({
      label: `Projection (${prediction.horizon_label})`,
      data: projData,
      borderColor: projColor, borderDash: [6, 5], borderWidth: 2,
      pointRadius: (ctx) => (ctx.dataIndex === labels.length - 1 ? 4 : 0),
      pointBackgroundColor: projColor, tension: 0, fill: false, spanGaps: true,
    });
  }

  if (priceChart) priceChart.destroy();
  priceChart = new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { labels: { color: cssVar("--muted"), boxWidth: 12 } },
        tooltip: { callbacks: { label: (c) => c.parsed.y == null ? null : `${c.dataset.label}: ${c.parsed.y.toFixed(2)}` } },
      },
      scales: {
        x: { ticks: { color: cssVar("--muted"), maxTicksLimit: 8 }, grid: { color: "rgba(255,255,255,0.04)" } },
        y: { ticks: { color: cssVar("--muted") }, grid: { color: "rgba(255,255,255,0.06)" } },
      },
    },
  });
}

function renderRecommendation(advice) {
  const recEl = document.getElementById("recommendation");
  recEl.textContent = advice.recommendation.replace(/_/g, " ");
  recEl.className = `rec r-${recClass(advice.recommendation)}`;
  document.getElementById("advice-summary").textContent = advice.summary;
}

function renderAnalyst(a, raw) {
  const wrap = document.getElementById("analyst");
  if (!a) { wrap.innerHTML = '<p class="muted">No analyst coverage available.</p>'; return; }

  const latest = (a.ratings && a.ratings[0]) || null;
  const segs = latest ? [
    ["Strong Buy", latest.strong_buy, "strong"],
    ["Buy", latest.buy, "healthy"],
    ["Hold", latest.hold, "neutral"],
    ["Sell", latest.sell, "weak"],
    ["Strong Sell", latest.strong_sell, "poor"],
  ] : [];
  const total = segs.reduce((s, x) => s + x[1], 0);

  const key = a.recommendation_key ? a.recommendation_key.replace(/_/g, " ") : "—";
  const mean = a.recommendation_mean != null ? a.recommendation_mean.toFixed(2) : "—";
  const nAn = a.num_analysts != null ? a.num_analysts : (total || "—");

  let bar = "";
  if (total > 0) {
    bar = '<div class="dist">' + segs.map(([name, n, cls]) =>
      n > 0 ? `<div class="dist-seg bg-${cls}" style="width:${(n / total) * 100}%" title="${name}: ${n}"></div>` : ""
    ).join("") + "</div>" +
      '<div class="dist-legend">' + segs.map(([name, n, cls]) =>
        `<span><i class="dot bg-${cls}"></i>${name} ${n}</span>`).join("") + "</div>";
  }

  // Price-target range bar (low — mean/current — high).
  let target = "";
  if (a.target_low != null && a.target_high != null && a.target_high > a.target_low) {
    const lo = a.target_low, hi = a.target_high;
    const pos = (v) => `${Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100))}%`;
    const cur = a.current_price ?? raw.price;
    target = `
      <div class="target">
        <div class="target-head"><span class="muted">12-mo price target</span>
          <span>${fmtMoney(a.target_mean, raw.currency)} avg</span></div>
        <div class="target-bar">
          <div class="target-fill"></div>
          ${cur != null ? `<span class="target-mark cur" style="left:${pos(cur)}" title="Current ${fmtMoney(cur, raw.currency)}"></span>` : ""}
          ${a.target_mean != null ? `<span class="target-mark mean" style="left:${pos(a.target_mean)}" title="Mean ${fmtMoney(a.target_mean, raw.currency)}"></span>` : ""}
        </div>
        <div class="target-ends"><span>${fmtMoney(lo, raw.currency)}</span><span>${fmtMoney(hi, raw.currency)}</span></div>
        <div class="target-legend"><span><i class="dot cur"></i>Current</span><span><i class="dot mean"></i>Mean target</span></div>
      </div>`;
  }

  wrap.innerHTML = `
    <div class="consensus">
      <div><span class="big r-${recClass(a.recommendation_key)}">${key}</span><span class="muted small">consensus</span></div>
      <div><span class="big">${mean}</span><span class="muted small">mean (1=buy…5=sell)</span></div>
      <div><span class="big">${nAn}</span><span class="muted small">analysts</span></div>
    </div>
    ${bar}
    ${target}`;
}

function renderStatements(statements) {
  const tabs = document.getElementById("stmt-tabs");
  const table = document.getElementById("stmt-table");
  tabs.innerHTML = "";
  if (!statements.length) { table.innerHTML = '<p class="muted">No financial statements available.</p>'; return; }

  statements.forEach((stmt, i) => {
    const btn = document.createElement("button");
    btn.className = "tab" + (i === 0 ? " active" : "");
    btn.textContent = stmt.title;
    btn.addEventListener("click", () => {
      tabs.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      drawTable(stmt);
    });
    tabs.appendChild(btn);
  });
  drawTable(statements[0]);
}

function drawTable(stmt) {
  const table = document.getElementById("stmt-table");
  const years = stmt.periods.map((p) => p.slice(0, 4));
  let html = "<table><thead><tr><th>Item</th>";
  years.forEach((y) => (html += `<th>${y}</th>`));
  html += '<th class="yoy">YoY</th><th class="avg">Avg</th></tr></thead><tbody>';
  for (const item of stmt.items) {
    html += `<tr><td class="item">${item.label}</td>`;
    item.values.forEach((v) => (html += `<td>${fmtBig(v, item.unit)}</td>`));
    const yoyCls = item.yoy_pct == null ? "" : (item.yoy_pct >= 0 ? "r-strong" : "r-poor");
    html += `<td class="yoy ${yoyCls}">${item.yoy_pct == null ? "—" : fmtPct(item.yoy_pct)}</td>`;
    html += `<td class="avg">${fmtBig(item.avg, item.unit)}</td></tr>`;
  }
  html += "</tbody></table>";
  table.innerHTML = html;
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
