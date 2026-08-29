import json
from datetime import date
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.cash_flow_engine import CashFlowEngine
from backend.risk_model import run_monte_carlo_forecast, DEFAULT_START_DATE

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
    currency: str = Query("USD", description="Target base currency (USD, EUR, GBP)"),
    days: int = Query(90, ge=1, le=180, description="Forecast horizon in days"),
    simulations: int = Query(1000, ge=100, le=10000, description="Number of Monte Carlo simulation runs"),
):
    engine = get_engine()
    return run_monte_carlo_forecast(
        engine=engine,
        days=days,
        target_currency=currency,
        n_simulations=simulations,
        base_date=DEFAULT_START_DATE,
    )


@app.post("/apply-action")
def apply_action(
    req: ApplyActionRequest,
    currency: str = Query("USD", description="Target base currency (USD, EUR, GBP)"),
    days: int = Query(90, ge=1, le=180, description="Forecast horizon in days"),
    simulations: int = Query(1000, ge=100, le=10000, description="Number of Monte Carlo simulation runs"),
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

    # Recompute and return the updated forecast immediately
    return run_monte_carlo_forecast(
        engine=engine,
        days=days,
        target_currency=currency,
        n_simulations=simulations,
        base_date=DEFAULT_START_DATE,
    )


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)