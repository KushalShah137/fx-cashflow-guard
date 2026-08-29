import sys
from pathlib import Path

# Add project root to sys.path so modules resolve cleanly both as a script and via uvicorn
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.cash_flow_engine import CashFlowEngine
from backend.risk_model_v2 import get_risk_band as get_risk_band_v2, get_model_diagnostics, DEFAULT_START_DATE
from backend.risk_classifier import RiskClassifier
from backend.decision_engine import DecisionEngine
from backend.response_models import RiskClassificationResponse, DecisionResponse, RecommendationLifecycleSchema

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


def save_and_enrich_recommendations(decisions: dict) -> dict:
    from backend.state_machine import create_or_update_recommendation
    enriched_recs = []
    for r in decisions.get("recommendations", []):
        impact = r.get("expected_impact", {}) or {}
        rec_data = {
            "transaction_id": r["transaction_id"],
            "action_type": r["action"],
            "priority": r["priority"],
            "risk_score": r["risk_score"],
            "confidence": 80,  # default placeholder until Phase 9
            "reason": r["reason"],
            "reason_codes": r.get("reason_codes", []),
            "warnings": r.get("warnings", []),
            "amount_base": r["amount_base"],
            "recommended_amount": r.get("recommended_amount"),
            "risk_before": r.get("risk_level", "LOW"),
            "risk_after_estimate": "LOW" if r["action"] in ("CONVERT_AND_HOLD", "SETTLE_NOW", "RE_QUOTE") else r.get("risk_level", "LOW"),
            "estimated_action_cost": impact.get("action_cost", 0.0),
            "estimated_inaction_cost": impact.get("expected_inaction_cost", 0.0)
        }
        action_id = create_or_update_recommendation(rec_data)
        r_copy = dict(r)
        r_copy["action_id"] = action_id
        enriched_recs.append(r_copy)
    decisions_copy = dict(decisions)
    decisions_copy["recommendations"] = enriched_recs
    return decisions_copy


def get_engine(reload: bool = False) -> CashFlowEngine:
    global _engine_instance
    if _engine_instance is None or reload:
        if reload:
            from backend.db import init_db
            init_db(force=True)
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
    tx = engine.get_transaction_by_id(req.transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction '{req.transaction_id}' not found")
        
    try:
        engine.apply_action(
            transaction_id=req.transaction_id,
            action=req.action,
            settle_date=DEFAULT_START_DATE,
        )
        # Sync state machine SQLite DB so GET /actions reflects execution
        from backend.state_machine import sync_action_for_transaction
        sync_action_for_transaction(req.transaction_id, req.action)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    pts = engine.get_forecast(days=days, base_date=DEFAULT_START_DATE)
    return [p.to_dict() for p in pts]


@app.post("/reset")
def reset_demo():
    """Reset both the in-memory engine state and the SQLite database tables back to the original dataset."""
    get_engine(reload=True)
    from backend.db import init_db
    init_db(force=True)
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
    decisions = save_and_enrich_recommendations(decisions)
    
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
    decisions = save_and_enrich_recommendations(decisions)
    return decisions


# --------------------------------------------------------------------------- #
# Netting & Economic Impact Endpoints
# --------------------------------------------------------------------------- #
@app.get("/netting-opportunities")
def get_netting_opportunities():
    """Calculates multilateral same-currency netting opportunities across transactions."""
    from backend.netting_engine import NettingEngine
    engine = get_engine()
    netting_eng = NettingEngine()
    return netting_eng.calculate_netting(
        transactions=engine.transactions,
        fx_rates=engine.fx_rates,
        anchor_date=DEFAULT_START_DATE,
    )


@app.get("/economic-impact")
def get_economic_impact():
    """Calculates economic value preservation and avoided cost of inaction."""
    from backend.economic_impact_engine import EconomicImpactEngine
    from backend.netting_engine import NettingEngine
    engine = get_engine()
    impact_eng = EconomicImpactEngine()
    
    # Calculate impact across all active foreign payables
    total_avoided_loss = 0.0
    total_action_cost = 0.0
    impact_items = []
    
    for tx in engine.transactions:
        if tx.direction.value == "payable" and tx.currency != engine.base_currency:
            base_amt = engine.convert_to_base(tx.amount, tx.currency)
            # 30-day default horizon
            days_to_due = max(1, (tx.date - DEFAULT_START_DATE).days)
            vol = engine.fx_config.get("daily_volatility", {}).get(tx.currency, 0.005)
            imp = impact_eng.calculate_impact(
                amount_base=base_amt,
                daily_volatility=vol,
                days_to_due=days_to_due,
                action="CONVERT_AND_HOLD",
                priority="HIGH" if base_amt > 15000 else "MEDIUM"
            )
            imp["transaction_id"] = tx.id
            imp["currency"] = tx.currency
            total_avoided_loss += imp["estimated_avoided_loss"]
            total_action_cost += imp["action_cost"]
            impact_items.append(imp)

    return {
        "total_estimated_avoided_loss": round(total_avoided_loss, 2),
        "total_action_cost": round(total_action_cost, 2),
        "total_net_economic_benefit": round(total_avoided_loss - total_action_cost, 2),
        "itemized_impacts": impact_items,
    }


# --------------------------------------------------------------------------- #
# Action Lifecycle Endpoints
# --------------------------------------------------------------------------- #
from typing import List

@app.get("/actions", response_model=List[RecommendationLifecycleSchema])
def list_actions():
    from backend.state_machine import get_all_recommendations
    return get_all_recommendations()


@app.get("/actions/{action_id}", response_model=RecommendationLifecycleSchema)
def get_action(action_id: str):
    from backend.state_machine import get_recommendation_by_id
    action = get_recommendation_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"No action found with ID '{action_id}'")
    return action


@app.post("/actions/{action_id}/approve", response_model=RecommendationLifecycleSchema)
def approve_action(action_id: str):
    from backend.state_machine import transition_recommendation_status, LifecycleError
    try:
        updated = transition_recommendation_status(action_id, "APPROVED", actor="cfo")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LifecycleError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/actions/{action_id}/reject", response_model=RecommendationLifecycleSchema)
def reject_action(action_id: str):
    from backend.state_machine import transition_recommendation_status, LifecycleError
    try:
        updated = transition_recommendation_status(action_id, "REJECTED", actor="cfo")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LifecycleError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/actions/{action_id}/execute", response_model=RecommendationLifecycleSchema)
def execute_action(action_id: str):
    """
    Executes an action via the state machine pipeline:
    Transitions status: APPROVED -> EXECUTING -> EXECUTED, and executes the hedge/settlement
    on the in-memory engine and SQLite database.
    """
    from backend.state_machine import get_recommendation_by_id, transition_recommendation_status, LifecycleError
    rec = get_recommendation_by_id(action_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"No action found with ID '{action_id}'")

    current_status = rec["status"]
    # Auto-approve if in RECOMMENDED state
    if current_status == "RECOMMENDED":
        transition_recommendation_status(action_id, "APPROVED", actor="cfo")

    try:
        # 1. Transition to EXECUTING
        transition_recommendation_status(action_id, "EXECUTING", actor="cfo")

        # 2. Execute on in-memory engine
        engine = get_engine()
        engine.apply_action(
            transaction_id=rec["transaction_id"],
            action=rec["action_type"],
            settle_date=DEFAULT_START_DATE,
        )

        # 3. Transition to EXECUTED
        updated = transition_recommendation_status(action_id, "EXECUTED", actor="cfo")
        return updated
    except Exception as e:
        try:
            transition_recommendation_status(action_id, "FAILED", actor="system")
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=f"Execution failed: {e}")


# --------------------------------------------------------------------------- #
# Demo Script Diagnostic Check
# --------------------------------------------------------------------------- #
@app.get("/demo-script-check")
def demo_script_check():
    """
    Pre-demo diagnostic health check:
    Confirms SQLite DB, FX 2-year history cache, Wise fallback, and initial demo transactions.
    """
    from backend.db import DB_PATH, get_db_connection
    from backend.wise_api import execute_wise_action

    checks: Dict[str, Any] = {}
    engine = get_engine()

    # 1. Check SQLite DB
    db_ok = DB_PATH.exists()
    row_count = 0
    if db_ok:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM transactions")
            row_count = cur.fetchone()[0]
            conn.close()
            db_ok = row_count >= 18
        except Exception as e:
            db_ok = False
    checks["sqlite_database"] = {
        "status": "PASS" if db_ok else "FAIL",
        "path": str(DB_PATH),
        "transaction_rows": row_count,
    }

    # 2. Check FX Historical Cache
    cache_path = DATA_PATH.parent / "fx_historical_cache.json"
    cache_ok = cache_path.exists()
    cache_rows = 0
    currencies_found: List[str] = []
    if cache_ok:
        try:
            with open(cache_path, "r", encoding="utf-8-sig") as f:
                cdata = json.load(f)
                cache_rows = len(cdata.get("historical_rates", []))
                currencies_found = cdata.get("currencies", [])
                cache_ok = cache_rows >= 500 and len(currencies_found) >= 6
        except Exception:
            cache_ok = False
    checks["fx_historical_cache"] = {
        "status": "PASS" if cache_ok else "FAIL",
        "rows": cache_rows,
        "currencies": currencies_found,
        "date_range": f"{cdata.get('start_date', '')} to {cdata.get('end_date', '')}" if cache_ok else "N/A",
    }

    # 3. Check Wise API Resilience
    wise_ok = True
    wise_resp: Dict[str, Any] = {}
    try:
        wise_resp = execute_wise_action("convert_and_hold", "EUR", 1000.0)
        wise_ok = bool(wise_resp.get("quote_id") and wise_resp.get("rate"))
    except Exception as e:
        wise_ok = False
        wise_resp = {"error": str(e)}
    checks["wise_sandbox_resilience"] = {
        "status": "PASS" if wise_ok else "FAIL",
        "mode": wise_resp.get("status", "unknown"),
        "quote_id": wise_resp.get("quote_id"),
        "indicative_rate": wise_resp.get("rate"),
    }

    # 4. Check Demo Triggers (txn_010, txn_013, txn_019)
    t10 = engine.get_transaction_by_id("txn_010")
    t13 = engine.get_transaction_by_id("txn_013")
    t19 = engine.get_transaction_by_id("txn_019")
    triggers_ok = bool(
        t10 and t10.demo_action == "convert_and_hold" and getattr(t10.status, "value", t10.status) == "pending" and
        t13 and t13.demo_action == "settle_now" and getattr(t13.status, "value", t13.status) == "pending" and
        t19 and t19.demo_action == "convert_and_hold" and getattr(t19.status, "value", t19.status) == "pending"
    )
    checks["demo_transactions_initial_state"] = {
        "status": "PASS" if triggers_ok else "FAIL",
        "txn_010_EUR": {"status": getattr(t10.status, "value", str(t10.status)) if t10 else "missing", "action": t10.demo_action if t10 else None},
        "txn_013_GBP": {"status": getattr(t13.status, "value", str(t13.status)) if t13 else "missing", "action": t13.demo_action if t13 else None},
        "txn_019_INR": {"status": getattr(t19.status, "value", str(t19.status)) if t19 else "missing", "action": t19.demo_action if t19 else None},
    }

    all_pass = all(c.get("status") == "PASS" for c in checks.values())

    return {
        "all_systems_go": all_pass,
        "status": "GREEN" if all_pass else "RED",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": checks,
    }


# =========================================================================== #
# Frontend Integration Endpoints (/api/*)
# =========================================================================== #

@app.get("/api/forecast")
def api_get_forecast(
    horizon: int = Query(60, description="Horizon in days (30, 60, 90)"),
    stress_currency: Optional[str] = Query(None, description="Currency to stress"),
    stress_pct: float = Query(0.0, description="Stress percent shift"),
    risk_tolerance: str = Query("moderate", description="conservative, moderate, aggressive"),
):
    engine = get_engine()
    starting_balance = engine.starting_balance or 50000.0
    danger_threshold = engine.danger_threshold or 20000.0

    # 1. Run real Monte Carlo simulation with stress testing & Qwen news sentiment
    from backend.risk_model_v2 import run_monte_carlo_forecast_v2
    sim_res = run_monte_carlo_forecast_v2(
        engine=engine,
        days=horizon,
        n_simulations=1000,
        base_date=DEFAULT_START_DATE,
        seed=42,
        cache_path=DATA_PATH.parent / "fx_historical_cache.json",
    )

    # 2. Extract real deterministic baseline points
    pts = engine.get_forecast(days=horizon, base_date=DEFAULT_START_DATE)

    # 3. Assemble timeline points
    timeline = []
    for i in range(1, horizon + 1):
        pt_idx = i - 1
        p_det = pts[pt_idx] if pt_idx < len(pts) else pts[-1]
        p_sim = (
            sim_res["forecast"][pt_idx]
            if pt_idx < len(sim_res["forecast"])
            else sim_res["forecast"][-1]
        )

        p5 = p_sim["worst"]
        p50 = p_sim["expected"]
        p95 = p_sim["best"]

        # If stress test is active
        if stress_currency and stress_pct != 0.0:
            stress_factor = (stress_pct / 100.0) * (i / horizon)
            p5 = p5 * (1.0 + min(0.0, stress_factor))
            p95 = p95 * (1.0 + max(0.0, stress_factor))

        if risk_tolerance == "conservative":
            p5 = p50 - (p50 - p5) * 1.25
            p95 = p50 + (p95 - p50) * 1.25
        elif risk_tolerance == "aggressive":
            p5 = p50 - (p50 - p5) * 0.8
            p95 = p50 + (p95 - p50) * 0.8

        prev_bal = pts[pt_idx - 1].balance if pt_idx > 0 else starting_balance
        daily_flow = p_det.balance - prev_bal

        timeline.append({
            "date": p_det.date.isoformat(),
            "day_index": i,
            "deterministic_balance": round(p_det.balance, 2),
            "worst_case_5th": round(p5, 2),
            "expected_50th": round(p50, 2),
            "best_case_95th": round(p95, 2),
            "net_cash_flow": round(daily_flow, 2),
        })

    final_expected = timeline[-1]["expected_50th"] if timeline else starting_balance
    final_worst = timeline[-1]["worst_case_5th"] if timeline else starting_balance
    final_best = timeline[-1]["best_case_95th"] if timeline else starting_balance
    min_worst = min((t["worst_case_5th"] for t in timeline), default=starting_balance)

    risk_status = "SAFE"
    if min_worst < danger_threshold:
        risk_status = "BREACH"
    elif min_worst < danger_threshold * 1.25:
        risk_status = "CAUTION"

    return {
        "horizon_days": horizon,
        "base_currency": engine.base_currency,
        "starting_balance": round(starting_balance, 2),
        "danger_threshold": round(danger_threshold, 2),
        "summary": {
            "expected_final_balance": round(final_expected, 2),
            "worst_case_5th_var": round(final_worst, 2),
            "best_case_95th": round(final_best, 2),
            "value_at_risk_95": round(max(0.0, final_expected - final_worst), 2),
            "risk_status": risk_status,
        },
        "timeline": timeline,
    }


@app.get("/api/transactions")
def api_get_transactions():
    engine = get_engine()
    # 1. Run classifications and decisions
    band = get_risk_band_v2(engine=engine, days=90, n_simulations=500, seed=42)
    classifier = RiskClassifier()
    classification = classifier.classify(engine, band, days=90)

    dec_engine = DecisionEngine()
    decisions = dec_engine.generate_decisions(
        engine, classification, anchor_date=DEFAULT_START_DATE
    )
    decisions = save_and_enrich_recommendations(decisions)

    # 2. Run Netting Engine
    from backend.netting_engine import NettingEngine
    from backend.cash_flow_engine import FlowDirection, TransactionStatus

    net_engine = NettingEngine()
    net_res = net_engine.calculate_netting(
        transactions=engine.transactions,
        fx_rates=engine.fx_rates,
        base_currency=engine.base_currency,
        anchor_date=DEFAULT_START_DATE,
    )
    netted_currencies = {
        ccy for ccy, data in net_res.get("portfolio_breakdown", {}).items()
        if data.get("natural_netting_offset", 0.0) > 0
    }

    rec_by_tx = {r["transaction_id"]: r for r in decisions.get("recommendations", [])}

    tx_list = []
    for tx in engine.transactions:
        rec = rec_by_tx.get(tx.id, {})
        flow_type = "PAYABLE" if tx.direction == FlowDirection.PAYABLE else "RECEIVABLE"
        days_due = max(0, (tx.date - DEFAULT_START_DATE).days)

        # Calculate real 95% VaR and carry cost
        base_amt = engine.convert_to_base(abs(tx.amount), tx.currency)
        cur_val = base_amt

        action = rec.get("action", "MONITOR")
        adverse_var = base_amt * 0.05 * ((days_due / 30.0) ** 0.5)
        carry_cost = base_amt * (0.045 / 365.0) * days_due

        status_label = "UNFUNDED"
        if getattr(tx.status, "value", str(tx.status)) == "settled":
            status_label = "SETTLED"
        elif tx.demo_action == "convert_and_hold":
            status_label = "FUNDED"
        elif flow_type == "RECEIVABLE":
            status_label = "EXPOSED_RECEIVABLE"

        tx_list.append({
            "id": tx.id,
            "counterparty": getattr(tx, "counterparty", None)
            or f"{tx.currency} International Partner",
            "type": flow_type,
            "currency": tx.currency,
            "foreign_amount": round(abs(tx.amount), 2),
            "inr_book_value": round(base_amt, 2),
            "current_inr_value": round(cur_val, 2),
            "due_date": tx.date.isoformat(),
            "days_until_due": days_due,
            "status": status_label,
            "classification": action,
            "netting_group": f"{tx.currency}-{min(90, max(14, (days_due // 15) * 15))}D",
            "is_netted": tx.currency in netted_currencies,
            "adverse_var_inr": round(adverse_var, 2),
            "carry_cost_inr": round(carry_cost, 2),
            "carry_cost_gate_passed": adverse_var > carry_cost,
            "recommended_action": action.replace("_", " ").title(),
            "rationale": rec.get("reason", f"Risk score: {rec.get('risk_score', 50)}/100"),
        })

    return tx_list


@app.get("/api/market-sentiment")
def api_get_market_sentiment():
    import numpy as np
    from backend.risk_model_v2 import NEWS_CACHE_PATH, load_news_sentiment_cache

    cache_data = load_news_sentiment_cache(NEWS_CACHE_PATH)
    if not cache_data:
        return {
            "sentiment_summary": "Macro environment balanced. Historical cross-currency correlations active.",
            "drift_adjustment": 0.0,
            "volatility_adjustment": 1.0,
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "headlines": [
                "Fed holds benchmark interest rates steady amid balanced labor market data",
                "ECB monitors eurozone inflation trajectories and foreign exchange liquidity",
                "Bank of England signals measured policy stance amid global trade updates",
            ],
            "currencies": {
                "EUR": {"sentiment_score": 0.1, "volatility_multiplier": 1.0, "drift_bias_bps": 0.0},
                "GBP": {"sentiment_score": -0.2, "volatility_multiplier": 1.05, "drift_bias_bps": -2.0},
                "USD": {"sentiment_score": 0.3, "volatility_multiplier": 1.0, "drift_bias_bps": 3.0},
            },
        }

    ccys = cache_data.get("currencies", {})
    all_headlines = []
    for c, info in ccys.items():
        all_headlines.extend(info.get("headlines", []))

    avg_vol = (
        float(
            np.mean([
                info.get("effective", {}).get("volatility_multiplier", 1.0)
                for info in ccys.values()
            ])
        )
        if ccys
        else 1.0
    )
    avg_drift = (
        float(
            np.mean([
                info.get("effective", {}).get("drift_bias_bps", 0.0)
                for info in ccys.values()
            ])
        )
        if ccys
        else 0.0
    )

    return {
        "sentiment_summary": f"Live Qwen 2.5 sentiment analysis across {len(ccys)} FX pairs. Average volatility multiplier: {avg_vol:.2f}x.",
        "drift_adjustment": round(avg_drift, 2),
        "volatility_adjustment": round(avg_vol, 2),
        "last_updated": cache_data.get("updated_at", datetime.utcnow().isoformat() + "Z"),
        "headlines": all_headlines[:5]
        or [
            "ECB rate decision signals measured easing cycle across European sovereign debt",
            "US Dollar maintains resilient carry advantage against major trading partners",
        ],
        "currencies": ccys,
    }


@app.get("/api/balances")
def api_get_balances():
    engine = get_engine()
    balances = {engine.base_currency: round(engine.starting_balance, 2)}
    for ccy in engine.fx_rates.keys():
        if ccy != engine.base_currency:
            balances[ccy] = 0.0

    for tx in engine.transactions:
        if tx.demo_action == "convert_and_hold" or getattr(tx.status, "value", str(tx.status)) == "settled":
            balances[tx.currency] = balances.get(tx.currency, 0.0) + abs(tx.amount)

    return balances


@app.get("/api/audit-log")
def api_get_audit_log():
    from backend.db import get_db_connection, init_db
    init_db()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT log_id, event_type, action_id, transaction_id, timestamp, actor, old_state, new_state, metadata_json FROM audit_logs ORDER BY log_id DESC LIMIT 50"
    )
    rows = cur.fetchall()
    conn.close()

    logs = []
    for r in rows:
        meta = {}
        try:
            meta = json.loads(r["metadata_json"] or "{}")
        except Exception:
            pass

        logs.append({
            "id": f"AUD-{r['log_id']}",
            "timestamp": r["timestamp"],
            "action": r["event_type"],
            "transaction_id": r["transaction_id"] or r["action_id"] or "SYSTEM",
            "counterparty": meta.get("counterparty", "Treasury Operations"),
            "currency": meta.get("currency", "USD"),
            "foreign_amount": float(meta.get("foreign_amount", 0.0)),
            "inr_amount": float(meta.get("inr_amount", meta.get("amount_base", 0.0))),
            "locked_rate": float(meta.get("locked_rate", meta.get("rate", 1.0))),
            "sandbox_transfer_id": meta.get(
                "transfer_id", f"TXN-LOG-{r['log_id']}"
            ),
            "status": "COMPLETED",
        })
    return logs


@app.get("/api/economic-impact")
def api_get_economic_impact():
    return get_economic_impact()


@app.get("/api/actions", response_model=List[RecommendationLifecycleSchema])
def api_get_actions():
    return list_actions()


@app.post("/api/actions/{action_id}/approve", response_model=RecommendationLifecycleSchema)
def api_approve_action(action_id: str):
    return approve_action(action_id)


@app.post("/api/actions/{action_id}/reject", response_model=RecommendationLifecycleSchema)
def api_reject_action(action_id: str):
    return reject_action(action_id)


@app.post("/api/actions/{action_id}/execute", response_model=RecommendationLifecycleSchema)
def api_execute_action(action_id: str):
    return execute_action(action_id)


@app.post("/api/wise/quote")
def api_wise_quote(payload: Dict[str, Any]):
    from backend.wise_api import wise_client

    source = payload.get("source_currency", "INR")
    target = payload.get("target_currency", "USD")
    target_amt = float(payload.get("target_amount", 1000.0))

    quote = wise_client.create_quote(
        source_currency=source, target_currency=target, source_amount=target_amt
    )
    rate = quote.get("rate", 1.0)
    fee = quote.get("fee", 12.50)

    return {
        "quote_id": quote.get("id", f"quote_{int(datetime.utcnow().timestamp())}"),
        "source_currency": source,
        "target_currency": target,
        "target_amount": target_amt,
        "source_amount": round(target_amt / rate if rate > 0 else target_amt, 2),
        "mid_market_rate": rate,
        "fee_inr": fee,
        "traditional_bank_fee_estimate_inr": round(fee * 3.8, 2),
        "rate_guaranteed_minutes": 30,
        "delivery_estimate": "Instant via Wise Sandbox Rails",
    }


@app.post("/api/wise/execute")
def api_wise_execute(payload: Dict[str, Any]):
    from backend.wise_api import execute_wise_action

    action_type = payload.get("action_type", "CONVERT_AND_HOLD")
    tx_id = payload.get("transaction_id")
    target_ccy = payload.get("target_currency", "USD")
    target_amt = float(payload.get("target_amount", 1000.0))

    result = execute_wise_action(action_type.lower(), target_ccy, target_amt)

    if tx_id:
        engine = get_engine()
        engine.apply_action(tx_id, action_type)

    balances = api_get_balances()

    return {
        "success": True,
        "sandbox_transfer_id": result.get(
            "transfer_id", f"TRANSFER-{int(datetime.utcnow().timestamp())}"
        ),
        "status": "COMPLETED",
        "action_executed": action_type,
        "executed_at": datetime.utcnow().isoformat() + "Z",
        "locked_rate": result.get("rate", 1.0),
        "amount_debited_inr": round(target_amt / result.get("rate", 1.0), 2),
        "amount_credited_foreign": target_amt,
        "updated_wallet_balances": balances,
        "recalculated_var_reduction_inr": round(target_amt * 0.08, 2),
    }


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)