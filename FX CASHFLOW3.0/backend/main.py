import sys
from pathlib import Path

# Add project root to sys.path so modules resolve cleanly both as a script and via uvicorn
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from datetime import date
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.cash_flow_engine import CashFlowEngine
from backend.risk_model_v2 import get_risk_band as get_risk_band_v2, get_model_diagnostics, DEFAULT_START_DATE
from backend.risk_classifier import RiskClassifier
from backend.decision_engine import DecisionEngine
from backend.response_models import RiskClassificationResponse, DecisionResponse

app = FastAPI(
    title="fx-cashflow-guard Backend",
    description="Real-time cash flow forecasting with FX risk modeling API",
    version="0.1.0",
)

# Enable CORS for local development and frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_transactions.json"

# In-memory singleton instance for live interactive demo state
_engine_instance: Optional[CashFlowEngine] = None


def get_engine(reload: bool = False) -> CashFlowEngine:
    global _engine_instance
    if _engine_instance is None or reload:
        _engine_instance = CashFlowEngine.from_file(DATA_PATH)
    return _engine_instance


class ApplyActionRequest(BaseModel):
    transaction_id: str
    action: str


def var_color_for_dir(direction: str) -> str:
    return "#ff1744" if direction == "payable" else "#00e676"


def generate_landing_page_html(engine: CashFlowEngine) -> str:
    threshold = engine.danger_threshold or 20000.0
    band_points = get_risk_band_v2(engine=engine, days=90, n_simulations=200, seed=42)
    min_p5 = min(p["p5"] for p in band_points) if band_points else engine.starting_balance
    has_breach = min_p5 < threshold
    status_label = "CRITICAL BREACH" if has_breach else "LIQUIDITY SAFE"
    status_color = "#ff1744" if has_breach else "#00e676"
    status_bg = "rgba(255, 23, 68, 0.15)" if has_breach else "rgba(0, 230, 118, 0.15)"
    
    exposures = engine.get_currency_exposures()
    currencies_str = ", ".join(e.currency for e in exposures) or "EUR, GBP, INR, CNY, JPY, AUD"
    demo_actions = engine.get_demo_actions()
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="30">
  <title>FX-Cashflow Guard // Telemetry Terminal</title>
  <style>
    :root {{
      --bg: #06090e;
      --paper: #0a0f18;
      --card: #0f172a;
      --border: #1e293b;
      --cyan: #00e5ff;
      --emerald: #00e676;
      --amber: #ffb300;
      --coral: #ff1744;
      --text: #f8fafc;
      --muted: #94a3b8;
      --font-mono: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-mono);
      padding: 24px;
      line-height: 1.5;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    header {{
      border-bottom: 2px solid var(--cyan);
      padding-bottom: 16px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .logo {{
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 1px;
      color: var(--cyan);
    }}
    .tagline {{
      font-size: 12px;
      color: var(--muted);
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      font-size: 11px;
      font-weight: 700;
      border-radius: 4px;
      border: 1px solid var(--border);
    }}
    .badge-breach {{
      color: {status_color};
      background: {status_bg};
      border-color: {status_color};
    }}
    .telemetry-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }}
    .telemetry-card {{
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 16px;
    }}
    .telemetry-card .label {{
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      margin-bottom: 6px;
    }}
    .telemetry-card .value {{
      font-size: 20px;
      font-weight: 700;
      color: var(--text);
    }}
    .section-title {{
      font-size: 13px;
      font-weight: 700;
      color: var(--cyan);
      margin-bottom: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .section-title::after {{
      content: '';
      flex: 1;
      height: 1px;
      background: var(--border);
    }}
    .dashboard-panel {{
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 20px;
      margin-bottom: 28px;
    }}
    .btn-main {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--cyan);
      color: #000;
      padding: 12px 24px;
      font-family: var(--font-mono);
      font-size: 13px;
      font-weight: 700;
      text-decoration: none;
      border-radius: 4px;
      transition: all 0.15s ease;
      margin-bottom: 16px;
    }}
    .btn-main:hover {{
      background: #80f2ff;
      box-shadow: 0 0 15px rgba(0, 229, 255, 0.4);
    }}
    .currency-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-top: 12px;
    }}
    .currency-pills span {{
      font-size: 11px;
      color: var(--muted);
      margin-right: 4px;
    }}
    .pill {{
      padding: 6px 12px;
      font-size: 11px;
      font-weight: 600;
      text-decoration: none;
      background: var(--card);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 4px;
      transition: all 0.15s;
    }}
    .pill:hover {{
      border-color: var(--cyan);
      color: var(--cyan);
    }}
    .pill-active {{
      background: rgba(0, 229, 255, 0.15);
      border-color: var(--cyan);
      color: var(--cyan);
    }}
    .api-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
      margin-bottom: 28px;
    }}
    .api-card {{
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 14px;
      text-decoration: none;
      color: inherit;
      display: block;
      transition: all 0.15s;
    }}
    .api-card:hover {{
      border-color: var(--cyan);
      transform: translateY(-1px);
    }}
    .api-card .method {{
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 3px;
      margin-right: 6px;
      background: rgba(0, 229, 255, 0.15);
      color: var(--cyan);
    }}
    .api-card .path {{
      font-size: 12px;
      font-weight: 700;
      color: var(--text);
    }}
    .api-card .desc {{
      font-size: 11px;
      color: var(--muted);
      margin-top: 6px;
    }}
    .demo-triggers {{
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 16px;
      margin-bottom: 28px;
    }}
    .demo-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
      margin-top: 10px;
    }}
    .demo-table th, .demo-table td {{
      padding: 8px 12px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }}
    .demo-table th {{
      color: var(--muted);
      font-size: 10px;
      text-transform: uppercase;
    }}
    .btn-action {{
      padding: 4px 8px;
      font-size: 10px;
      font-weight: 700;
      background: rgba(255, 179, 0, 0.2);
      color: var(--amber);
      border: 1px solid var(--amber);
      border-radius: 3px;
      cursor: pointer;
      font-family: var(--font-mono);
    }}
    .btn-action:hover {{
      background: var(--amber);
      color: #000;
    }}
    footer {{
      margin-top: 40px;
      padding-top: 16px;
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <div class="logo">FX-CASHFLOW GUARD <span style="font-size: 12px; color: var(--muted);">// v0.1.0</span></div>
        <div class="tagline">Real-Time Multi-Currency Cash Flow Forecasting & Correlated FX Risk Modeling</div>
      </div>
      <div style="display: flex; align-items: center; gap: 10px;">
        <span class="badge badge-breach" id="live-badge">{status_label}</span>
        <button class="btn-action" onclick="resetState()">↺ RESET DEMO STATE</button>
      </div>
    </header>

    <!-- Telemetry Strip -->
    <div class="telemetry-grid">
      <div class="telemetry-card">
        <div class="label">Starting Cash</div>
        <div class="value" style="color: var(--emerald);">${engine.starting_balance:,.0f} <span style="font-size: 11px; color: var(--muted);">{engine.base_currency}</span></div>
      </div>
      <div class="telemetry-card">
        <div class="label">Danger Floor</div>
        <div class="value" style="color: var(--coral);">${threshold:,.0f} <span style="font-size: 11px; color: var(--muted);">FLOOR</span></div>
      </div>
      <div class="telemetry-card">
        <div class="label">Simulated P5 Min</div>
        <div class="value" style="color: {status_color};">${min_p5:,.0f}</div>
      </div>
      <div class="telemetry-card">
        <div class="label">Active Ledger</div>
        <div class="value">{len(engine.transactions)} <span style="font-size: 11px; color: var(--muted);">TXNS</span></div>
      </div>
      <div class="telemetry-card">
        <div class="label">FX Currencies</div>
        <div class="value" style="font-size: 13px; color: var(--cyan);">{len(exposures)} Pairs <span style="font-size: 10px; color: var(--muted);">({currencies_str})</span></div>
      </div>
    </div>

    <!-- Visualization Telemetry Hub -->
    <div class="section-title">📊 Visual Telemetry & Analytics Dashboard</div>
    <div class="dashboard-panel">
      <p style="font-size: 12px; color: var(--muted); margin-bottom: 16px;">
        High-density, 4-panel Bloomberg-terminal-styled financial telemetry view combining 90-day simulated risk bands, net currency exposure matrix, real 2-year annualized volatility, and active transaction ledger.
      </p>
      <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center;">
        <a class="btn-main" href="/viz/dashboard?currency=USD&days=90" target="_blank">
          ▶ LAUNCH INTERACTIVE TERMINAL (USD 90D)
        </a>
        <a class="pill" href="/viz/dashboard.png?currency=USD&days=90" target="_blank" style="padding: 12px 16px;">
          📷 STATIC PNG EXPORT
        </a>
      </div>

      <div class="currency-pills">
        <span>Quick Currency Switcher:</span>
        <a class="pill pill-active" href="/viz/dashboard?currency=USD&days=90" target="_blank">USD Base</a>
        <a class="pill" href="/viz/dashboard?currency=EUR&days=90" target="_blank">EUR Base</a>
        <a class="pill" href="/viz/dashboard?currency=GBP&days=90" target="_blank">GBP Base</a>
        <a class="pill" href="/viz/dashboard?currency=INR&days=90" target="_blank">INR Base</a>
        <a class="pill" href="/viz/dashboard?currency=CNY&days=90" target="_blank">CNY Base</a>
        <a class="pill" href="/viz/dashboard?currency=JPY&days=90" target="_blank">JPY Base</a>
        <a class="pill" href="/viz/dashboard?currency=AUD&days=90" target="_blank">AUD Base</a>
      </div>
    </div>

    <!-- Live Demo Actions Strip -->
    <div class="section-title">⚡ Live Demo Trigger Points (Hedging & Settlement)</div>
    <div class="demo-triggers">
      <table class="demo-table">
        <thead>
          <tr>
            <th>Txn ID</th>
            <th>Description</th>
            <th>Date</th>
            <th>Amount</th>
            <th>Action Type</th>
            <th>Trigger Simulation</th>
          </tr>
        </thead>
        <tbody>
          {"".join(f'''<tr>
            <td style="font-weight:700; color:var(--cyan);">{tx["transaction_id"]}</td>
            <td>{tx["description"]}</td>
            <td>{tx["date"]}</td>
            <td style="color:{var_color_for_dir(tx["direction"])};">{tx["currency"]} {tx["amount"]:,.0f}</td>
            <td><span class="badge" style="color:var(--amber); border-color:var(--amber);">{tx["action"]}</span></td>
            <td><button class="btn-action" onclick="applyAction('{tx["transaction_id"]}', '{tx["action"]}')">EXECUTE {tx["action"].upper()}</button></td>
          </tr>''' for tx in demo_actions)}
        </tbody>
      </table>
    </div>

    <!-- Core API Endpoints Directory -->
    <div class="section-title">⚡ Core API Endpoints & Contracts</div>
    <div class="api-grid">
      <a class="api-card" href="/docs" target="_blank">
        <div><span class="method">UI</span><span class="path">/docs</span></div>
        <div class="desc">Interactive Swagger API documentation & testing sandbox.</div>
      </a>
      <a class="api-card" href="/risk-overview?days=90" target="_blank">
        <div><span class="method">GET</span><span class="path">/risk-overview</span></div>
        <div class="desc">Unified full payload: baseline forecast, risk bands, classifications, exposures & decisions.</div>
      </a>
      <a class="api-card" href="/decisions?days=90" target="_blank">
        <div><span class="method">GET</span><span class="path">/decisions</span></div>
        <div class="desc">Layer 3 Decision Engine actionable hedging and settlement recommendations.</div>
      </a>
      <a class="api-card" href="/risk-classification?days=90" target="_blank">
        <div><span class="method">GET</span><span class="path">/risk-classification</span></div>
        <div class="desc">Layer 2.5 Multi-Horizon (30D/60D/90D) risk scores, trajectory & liquidity status.</div>
      </a>
      <a class="api-card" href="/risk-band?days=90&simulations=1000" target="_blank">
        <div><span class="method">GET</span><span class="path">/risk-band</span></div>
        <div class="desc">Layer 2 Correlated Monte Carlo Value-at-Risk bands (P5, P50, P95 percentiles).</div>
      </a>
      <a class="api-card" href="/forecast?currency=USD&days=90" target="_blank">
        <div><span class="method">GET</span><span class="path">/forecast</span></div>
        <div class="desc">Layer 1 deterministic daily cash balance baseline projection.</div>
      </a>
      <a class="api-card" href="/exposures" target="_blank">
        <div><span class="method">GET</span><span class="path">/exposures</span></div>
        <div class="desc">Currency exposure matrix across EUR, GBP, INR, CNY, JPY, AUD.</div>
      </a>
      <a class="api-card" href="/transactions" target="_blank">
        <div><span class="method">GET</span><span class="path">/transactions</span></div>
        <div class="desc">Active transaction ledger (26 normalized records with demo tags).</div>
      </a>
      <a class="api-card" href="/viz/health" target="_blank">
        <div><span class="method">GET</span><span class="path">/viz/health</span></div>
        <div class="desc">Telemetry visualization engine health check and endpoint directory.</div>
      </a>
    </div>

    <footer>
      <div>FX-Cashflow Guard &bull; Hackathon Edition</div>
      <div>Real-Time European Central Bank Rates via Frankfurter.dev &bull; Wise Sandbox Integration Ready</div>
    </footer>
  </div>

  <script>
    async function applyAction(txId, action) {{
      try {{
        const res = await fetch('/apply-action', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ transaction_id: txId, action: action }})
        }});
        if (res.ok) {{
          alert('Action ' + action + ' successfully executed for ' + txId + '! Reloading telemetry...');
          window.location.reload();
        }} else {{
          const err = await res.json();
          alert('Error executing action: ' + JSON.stringify(err));
        }}
      }} catch (e) {{
        alert('Network error: ' + e);
      }}
    }}

    async function resetState() {{
      try {{
        const res = await fetch('/reset', {{ method: 'POST' }});
        if (res.ok) {{
          alert('Engine state successfully reset to initial mock ledger.');
          window.location.reload();
        }}
      }} catch (e) {{
        alert('Error: ' + e);
      }}
    }}
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root_landing_page():
    engine = get_engine()
    return HTMLResponse(content=generate_landing_page_html(engine), status_code=200)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/transactions")
def get_transactions():
    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)


@app.get("/forecast")
def get_forecast(
    currency: str = Query("USD", description="Target base currency (USD, EUR, GBP) (compatibility parameter, ignored in V2 baseline)"),
    days: int = Query(90, ge=1, le=180, description="Forecast horizon in days"),
    simulations: int = Query(1000, ge=100, le=10000, description="Number of Monte Carlo simulation runs (ignored in V2 baseline)"),
):
    engine = get_engine()
    pts = engine.get_forecast(days=days, base_date=DEFAULT_START_DATE)
    return [p.to_dict() for p in pts]


@app.post("/apply-action")
def apply_action(
    req: ApplyActionRequest,
    currency: str = Query("USD", description="Target base currency (USD, EUR, GBP) (ignored)"),
    days: int = Query(90, ge=1, le=180, description="Forecast horizon in days"),
    simulations: int = Query(1000, ge=100, le=10000, description="Number of Monte Carlo simulation runs (ignored)"),
):
    engine = get_engine()
    try:
        engine.apply_action(
            transaction_id=req.transaction_id,
            action=req.action,
            settle_date=DEFAULT_START_DATE,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    pts = engine.get_forecast(days=days, base_date=DEFAULT_START_DATE)
    return [p.to_dict() for p in pts]


@app.post("/reset")
def reset_demo():
    """Reset the engine state back to the original mock dataset."""
    get_engine(reload=True)
    return {"status": "reset_successful"}


@app.get("/exposures")
def get_exposures():
    engine = get_engine()
    return [e.to_dict() for e in engine.get_currency_exposures()]


@app.get("/demo-actions")
def get_demo_actions():
    engine = get_engine()
    return engine.get_demo_actions()


@app.get("/risk-band")
def risk_band(
    days: int = Query(90, ge=1, le=180, description="Forecast horizon in days"),
    simulations: int = Query(2000, ge=10, le=10000, description="Number of Monte Carlo simulation runs"),
):
    engine = get_engine()
    band = get_risk_band_v2(
        engine=engine,
        days=days,
        n_simulations=simulations,
        seed=42,
        cache_path=DATA_PATH.parent / "fx_historical_cache.json"
    )
    return {
        "days": days,
        "simulations": simulations,
        "currency": engine.base_currency,
        "risk_band": band
    }


@app.get("/risk-diagnostics")
def risk_diagnostics():
    cache_path = DATA_PATH.parent / "fx_historical_cache.json"
    return get_model_diagnostics(cache_path=cache_path)


@app.get("/risk-classification", response_model=RiskClassificationResponse)
def risk_classification(
    days: int = Query(90, ge=90, le=180, description="Forecast horizon in days (minimum 90)"),
    simulations: int = Query(2000, ge=10, le=10000, description="Number of Monte Carlo simulation runs"),
):
    engine = get_engine()
    band = get_risk_band_v2(
        engine=engine,
        days=days,
        n_simulations=simulations,
        seed=42,
        cache_path=DATA_PATH.parent / "fx_historical_cache.json"
    )
    classifier = RiskClassifier()
    classification = classifier.classify(engine, band, days=days)
    return classification


@app.get("/risk-overview")
def risk_overview(
    days: int = Query(90, ge=90, le=180, description="Forecast horizon in days (minimum 90)"),
    simulations: int = Query(2000, ge=10, le=10000, description="Number of Monte Carlo simulation runs"),
):
    engine = get_engine()
    # 1. Compute deterministic Layer 1 baseline forecast
    pts = engine.get_forecast(days=days, base_date=DEFAULT_START_DATE)
    baseline_list = [p.to_dict() for p in pts]
    
    # 2. Retrieve simulated risk band from V2 engine
    band = get_risk_band_v2(
        engine=engine,
        days=days,
        n_simulations=simulations,
        seed=42,
        cache_path=DATA_PATH.parent / "fx_historical_cache.json"
    )
    
    # 3. Run classification
    classifier = RiskClassifier()
    classification = classifier.classify(engine, band, days=days)
    
    # 4. Feed into Decision Engine
    dec_engine = DecisionEngine()
    decisions = dec_engine.generate_decisions(engine, classification, anchor_date=DEFAULT_START_DATE)
    
    # 5. Extract exposures
    exposures = [e.to_dict() for e in engine.get_currency_exposures()]
    
    return {
        "baseline_forecast": baseline_list,
        "risk_band": band,
        "risk_classification": classification,
        "exposures": exposures,
        "decisions": decisions
    }


@app.get("/decisions", response_model=DecisionResponse)
def get_decisions(
    days: int = Query(90, ge=90, le=180, description="Forecast horizon in days (minimum 90)"),
    simulations: int = Query(2000, ge=10, le=10000, description="Number of Monte Carlo simulation runs"),
):
    engine = get_engine()
    band = get_risk_band_v2(
        engine=engine,
        days=days,
        n_simulations=simulations,
        seed=42,
        cache_path=DATA_PATH.parent / "fx_historical_cache.json"
    )
    classifier = RiskClassifier()
    classification = classifier.classify(engine, band, days=days)
    
    dec_engine = DecisionEngine()
    decisions = dec_engine.generate_decisions(engine, classification, anchor_date=DEFAULT_START_DATE)
    return decisions


# --------------------------------------------------------------------------- #
# Visualization Endpoints (Bloomberg-Terminal Style)
# --------------------------------------------------------------------------- #
from fastapi.responses import HTMLResponse, Response
from backend.visualization import get_dashboard_html, get_dashboard_png_bytes


@app.get("/viz/health")
def viz_health():
    """Health check for the standalone visualization telemetry module."""
    return {
        "status": "ok",
        "module": "backend.visualization",
        "theme": "bloomberg_terminal_dark",
        "panels": [
            "90-Day Cash Flow Risk Bands & Danger Floor",
            "Multi-Currency Net Exposure Matrix",
            "Real 2-Year Historical FX Volatility",
            "90-Day Transaction Flow Timeline & Hedge Triggers",
        ],
        "endpoints": [
            "/viz/dashboard",
            "/viz/dashboard.png",
            "/viz/health",
        ],
    }


@app.get("/viz/dashboard", response_class=HTMLResponse)
def viz_dashboard(
    currency: str = Query("USD", description="Target base currency (USD, EUR, GBP)"),
    days: int = Query(90, ge=1, le=180, description="Forecast horizon in days"),
):
    """
    Renders the live multi-panel Bloomberg-terminal-style dashboard as standalone interactive HTML.
    """
    engine = get_engine()
    html_content = get_dashboard_html(engine=engine, currency=currency, days=days)
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/viz/dashboard.png")
def viz_dashboard_png(
    currency: str = Query("USD", description="Target base currency (USD, EUR, GBP)"),
    days: int = Query(90, ge=1, le=180, description="Forecast horizon in days"),
):
    """
    Renders the live multi-panel Bloomberg-terminal-style dashboard as a static PNG image.
    """
    engine = get_engine()
    png_bytes = get_dashboard_png_bytes(engine=engine, currency=currency, days=days)
    return Response(content=png_bytes, media_type="image/png")



# --------------------------------------------------------------------------- #
# Direct /api/* REST Endpoints (Frontend API Contract)
# --------------------------------------------------------------------------- #

class ApiWiseQuoteRequest(BaseModel):
    source_currency: str = "INR"
    target_currency: str = "USD"
    target_amount: float = 20000.0


class ApiWiseExecuteRequest(BaseModel):
    quote_id: str
    action_type: str  # CONVERT_AND_HOLD or SETTLE_NOW
    transaction_id: str
    target_currency: str
    target_amount: float
    source_amount: float


_api_wallet_balances = {
    "INR": 8251800.0,
    "USD": 20000.0,
    "EUR": 15000.0,
    "GBP": 0.0,
}

_api_audit_logs = [
    {
        "id": "AUD-9912",
        "timestamp": "2026-08-28 16:45:10",
        "action": "CONVERT_AND_HOLD",
        "transaction_id": "TX-098",
        "counterparty": "Stripe US Infrastructure",
        "currency": "USD",
        "foreign_amount": 14500.0,
        "inr_amount": 1267445.0,
        "locked_rate": 87.41,
        "sandbox_transfer_id": "TRX-WISE-SBX-8839102",
        "status": "COMPLETED",
    },
    {
        "id": "AUD-9911",
        "timestamp": "2026-08-25 11:20:00",
        "action": "SETTLE_NOW",
        "transaction_id": "TX-094",
        "counterparty": "AWS Frankfurt Node",
        "currency": "EUR",
        "foreign_amount": 8200.0,
        "inr_amount": 762600.0,
        "locked_rate": 93.0,
        "sandbox_transfer_id": "TRX-WISE-SBX-8711094",
        "status": "COMPLETED",
    },
]


@app.get("/api/forecast")
def api_get_forecast(
    horizon: int = Query(60, description="Horizon in days (30, 60, 90)"),
    stress_currency: Optional[str] = Query(None, description="Currency to stress"),
    stress_pct: float = Query(0.0, description="Stress percent shift"),
    risk_tolerance: str = Query("moderate", description="conservative, moderate, aggressive"),
):
    engine = get_engine()
    starting_balance = engine.starting_balance or 1000000.0
    danger_threshold = engine.danger_threshold or 450000.0

    multiplier = 1.35 if risk_tolerance == "conservative" else 0.75 if risk_tolerance == "aggressive" else 1.0

    stress_shift = 0.0
    if stress_currency == "USD":
        stress_shift = (stress_pct / 100.0) * 850000.0
    elif stress_currency == "EUR":
        stress_shift = (stress_pct / 100.0) * 450000.0
    elif stress_currency == "INR_CRASH":
        stress_shift = -abs(stress_pct / 100.0) * 1200000.0

    from datetime import timedelta
    timeline = []
    running_det = starting_balance
    base_d = date(2026, 9, 1)

    for i in range(1, horizon + 1):
        cur_d = base_d + timedelta(days=i - 1)
        day_flow = 0.0
        if i == 14:
            day_flow -= 1395000.0
        if i == 30:
            day_flow -= 1748200.0
        if i == 34:
            day_flow -= 936700.0
        if i == 47:
            day_flow += (1512000.0 - 1048800.0)
        if i == 83:
            day_flow -= 842000.0
        if i % 7 == 0:
            day_flow += 380000.0
        if i % 15 == 0:
            day_flow -= 220000.0

        running_det += day_flow
        dispersion = (i ** 0.5) * 18500.0 * multiplier * (1.0 + abs(stress_pct) / 20.0)
        expected = running_det + (stress_shift * (i / horizon))
        worst = expected - dispersion * 1.645 - max(0.0, -stress_shift * (i / horizon))
        best = expected + dispersion * 1.645 + max(0.0, stress_shift * (i / horizon))

        timeline.append({
            "date": cur_d.isoformat(),
            "day_index": i,
            "deterministic_balance": round(running_det, 2),
            "worst_case_5th": round(worst, 2),
            "expected_50th": round(expected, 2),
            "best_case_95th": round(best, 2),
            "net_cash_flow": round(day_flow, 2),
        })

    final_expected = timeline[-1]["expected_50th"]
    final_worst = timeline[-1]["worst_case_5th"]
    final_best = timeline[-1]["best_case_95th"]
    min_worst = min(t["worst_case_5th"] for t in timeline)

    risk_status = "SAFE"
    if min_worst < danger_threshold:
        risk_status = "BREACH"
    elif min_worst < danger_threshold * 1.25:
        risk_status = "CAUTION"

    return {
        "horizon_days": horizon,
        "base_currency": "INR",
        "starting_balance": starting_balance,
        "danger_threshold": danger_threshold,
        "summary": {
            "expected_final_balance": final_expected,
            "worst_case_5th_var": final_worst,
            "best_case_95th": final_best,
            "value_at_risk_95": max(0.0, final_expected - final_worst),
            "risk_status": risk_status,
        },
        "timeline": timeline,
    }


@app.get("/api/transactions")
def api_get_transactions():
    return [
        {
            "id": "TX-101",
            "counterparty": "Apex Cloud Systems (US)",
            "type": "PAYABLE",
            "currency": "USD",
            "foreign_amount": 20000.0,
            "inr_book_value": 1720000.0,
            "current_inr_value": 1748200.0,
            "due_date": "2026-09-28",
            "days_until_due": 30,
            "status": "UNFUNDED",
            "classification": "CONVERT_AND_HOLD",
            "netting_group": "USD-30D",
            "is_netted": False,
            "adverse_var_inr": 86000.0,
            "carry_cost_inr": 14200.0,
            "carry_cost_gate_passed": True,
            "recommended_action": "Convert & Hold",
            "rationale": "Adverse 95% VaR (₹86,000) significantly exceeds 30-day carry cost (₹14,200). Lock USD now.",
        },
        {
            "id": "TX-102",
            "counterparty": "Berlin Dev Studio GmbH",
            "type": "PAYABLE",
            "currency": "EUR",
            "foreign_amount": 15000.0,
            "inr_book_value": 1395000.0,
            "current_inr_value": 1395000.0,
            "due_date": "2026-09-12",
            "days_until_due": 14,
            "status": "FUNDED",
            "classification": "SETTLE_NOW",
            "netting_group": "EUR-14D",
            "is_netted": False,
            "adverse_var_inr": 0.0,
            "carry_cost_inr": 0.0,
            "carry_cost_gate_passed": False,
            "recommended_action": "Settle Now",
            "rationale": "EUR balance already funded and sitting idle. Settle invoice immediately to eliminate settlement friction.",
        },
        {
            "id": "TX-103",
            "counterparty": "Nordic Retailers AB",
            "type": "RECEIVABLE",
            "currency": "USD",
            "foreign_amount": 18000.0,
            "inr_book_value": 1548000.0,
            "current_inr_value": 1512000.0,
            "due_date": "2026-10-15",
            "days_until_due": 47,
            "status": "EXPOSED_RECEIVABLE",
            "classification": "RE_QUOTE_OR_HEDGE",
            "netting_group": "USD-45D",
            "is_netted": False,
            "adverse_var_inr": 62000.0,
            "carry_cost_inr": 0.0,
            "carry_cost_gate_passed": False,
            "recommended_action": "Re-Quote / Dynamic Buffer",
            "rationale": "USD receivable at risk of rupee appreciation. Consider adding a 1.5% FX buffer on next contract renewal.",
        },
        {
            "id": "TX-104",
            "counterparty": "London Design Syndicate",
            "type": "PAYABLE",
            "currency": "GBP",
            "foreign_amount": 8500.0,
            "inr_book_value": 935000.0,
            "current_inr_value": 936700.0,
            "due_date": "2026-10-02",
            "days_until_due": 34,
            "status": "UNFUNDED",
            "classification": "CONVERT_AND_HOLD",
            "netting_group": "GBP-30D",
            "is_netted": False,
            "adverse_var_inr": 42500.0,
            "carry_cost_inr": 7800.0,
            "carry_cost_gate_passed": True,
            "recommended_action": "Convert & Hold",
            "rationale": "GBP volatility elevated post Bank of England rates meeting. VaR exceeds hurdle rate.",
        },
        {
            "id": "TX-105",
            "counterparty": "Kyoto Electronics",
            "type": "PAYABLE",
            "currency": "USD",
            "foreign_amount": 12000.0,
            "inr_book_value": 1044000.0,
            "current_inr_value": 1048800.0,
            "due_date": "2026-10-15",
            "days_until_due": 47,
            "status": "UNFUNDED",
            "classification": "NATURALLY_NETTED",
            "netting_group": "USD-45D",
            "is_netted": True,
            "adverse_var_inr": 18000.0,
            "carry_cost_inr": 4100.0,
            "carry_cost_gate_passed": False,
            "recommended_action": "Hold (Natural Net)",
            "rationale": "Matched against TX-103 ($18,000 receivable). Net exposure is only $6,000 credit. No forward lock required.",
        },
        {
            "id": "TX-106",
            "counterparty": "Munich SaaS Logistics",
            "type": "PAYABLE",
            "currency": "EUR",
            "foreign_amount": 9000.0,
            "inr_book_value": 837000.0,
            "current_inr_value": 842000.0,
            "due_date": "2026-11-20",
            "days_until_due": 83,
            "status": "UNFUNDED",
            "classification": "CONVERT_AND_HOLD",
            "netting_group": "EUR-90D",
            "is_netted": False,
            "adverse_var_inr": 54000.0,
            "carry_cost_inr": 11200.0,
            "carry_cost_gate_passed": True,
            "recommended_action": "Convert & Hold",
            "rationale": "Quarterly server infrastructure invoice. Unhedged tail risk pushes horizon balance near danger floor.",
        },
    ]


@app.get("/api/market-sentiment")
def api_get_market_sentiment():
    return {
        "sentiment_summary": "Cautious on INR due to oil imports; USD resilient",
        "drift_adjustment": 0.03,
        "volatility_adjustment": 0.08,
        "last_updated": "2026-08-29T21:45:00Z",
        "headlines": [
            "Crude prices put pressure on emerging market currencies",
            "US Fed signals higher-for-longer policy trajectory",
            "RBI maintains strategic foreign exchange intervention corridor",
        ],
    }


@app.post("/api/wise/quote")
def api_post_wise_quote(req: ApiWiseQuoteRequest):
    rates = {"USD": 87.41, "EUR": 93.0, "GBP": 110.2}
    rate = rates.get(req.target_currency.upper(), 87.41)
    source_amount = round(req.target_amount * rate, 2)
    fee_inr = round(source_amount * 0.0028, 2)
    bank_fee = round(source_amount * 0.02, 2)

    import random
    quote_id = f"Q-WISE-{random.randint(100000, 999999)}"

    return {
        "quote_id": quote_id,
        "source_currency": req.source_currency.upper(),
        "target_currency": req.target_currency.upper(),
        "target_amount": req.target_amount,
        "source_amount": source_amount + fee_inr,
        "mid_market_rate": rate,
        "fee_inr": fee_inr,
        "traditional_bank_fee_estimate_inr": bank_fee,
        "rate_guaranteed_minutes": 30,
        "delivery_estimate": "Instant / Within 2 hours",
    }


@app.post("/api/wise/execute")
def api_post_wise_execute(req: ApiWiseExecuteRequest):
    import random
    from datetime import datetime

    target_curr = req.target_currency.upper()
    if target_curr in _api_wallet_balances:
        _api_wallet_balances[target_curr] += req.target_amount
    _api_wallet_balances["INR"] = max(0.0, _api_wallet_balances["INR"] - req.source_amount)

    trx_id = f"TRX-WISE-SBX-{random.randint(1000000, 9999999)}"
    now_iso = datetime.utcnow().isoformat() + "Z"

    _api_audit_logs.insert(0, {
        "id": f"AUD-{random.randint(1000, 9999)}",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "action": req.action_type,
        "transaction_id": req.transaction_id,
        "counterparty": f"Wise Multi-Currency ({target_curr})",
        "currency": target_curr,
        "foreign_amount": req.target_amount,
        "inr_amount": req.source_amount,
        "locked_rate": round(req.source_amount / max(1.0, req.target_amount), 2),
        "sandbox_transfer_id": trx_id,
        "status": "COMPLETED",
    })

    return {
        "success": True,
        "sandbox_transfer_id": trx_id,
        "status": "COMPLETED",
        "action_executed": req.action_type,
        "executed_at": now_iso,
        "locked_rate": round(req.source_amount / max(1.0, req.target_amount), 2),
        "amount_debited_inr": req.source_amount,
        "amount_credited_foreign": req.target_amount,
        "updated_wallet_balances": dict(_api_wallet_balances),
        "recalculated_var_reduction_inr": 86000.0,
    }


@app.get("/api/balances")
def api_get_balances():
    return _api_wallet_balances


@app.get("/api/audit-log")
def api_get_audit_log():
    return _api_audit_logs


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)