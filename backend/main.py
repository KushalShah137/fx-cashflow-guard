import json
from datetime import date
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.cash_flow_engine import CashFlowEngine
from backend.risk_model import run_monte_carlo_forecast
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
    # 1. Retrieve simulated risk band from V2 engine
    band = get_risk_band_v2(
        engine=engine,
        days=days,
        n_simulations=simulations,
        seed=42,
        cache_path=DATA_PATH.parent / "fx_historical_cache.json"
    )
    # 2. Run risk classification layer on top
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
    # 1. Retrieve simulated risk band from V2 engine
    band = get_risk_band_v2(
        engine=engine,
        days=days,
        n_simulations=simulations,
        seed=42,
        cache_path=DATA_PATH.parent / "fx_historical_cache.json"
    )
    # 2. Run risk classification layer on top
    classifier = RiskClassifier()
    classification = classifier.classify(engine, band, days=days)
    
    # 3. Feed into Decision Engine
    dec_engine = DecisionEngine()
    decisions = dec_engine.generate_decisions(engine, classification, anchor_date=DEFAULT_START_DATE)
    return decisions



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)