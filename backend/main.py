import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

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


def load_mock_data():
    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/transactions")
def get_transactions():
    return load_mock_data()


@app.get("/forecast")
def get_forecast(
    currency: str = Query("USD", description="Target base currency (USD, EUR, GBP)"),
    days: int = Query(90, ge=1, le=180, description="Forecast horizon in days"),
):
    # Stub response matching the approved contract exactly
    data = load_mock_data()
    danger_threshold = data.get("danger_threshold", 20000.0)
    starting_balance = data.get("starting_balance", 50000.0)

    return {
        "currency": currency.upper(),
        "starting_balance": starting_balance,
        "danger_threshold": danger_threshold,
        "has_breach": True,
        "breach_dates": [
            "2026-09-15",
            "2026-09-16",
        ],
        "summary": {
            "min_worst_case": 14250.0,
            "max_best_case": 89400.0,
            "final_expected": 62300.0,
        },
        "forecast": [
            {
                "date": "2026-08-29",
                "best": 50000.0,
                "expected": 50000.0,
                "worst": 50000.0,
                "net_change": 0.0,
            },
            {
                "date": "2026-08-30",
                "best": 54200.5,
                "expected": 53500.0,
                "worst": 51800.2,
                "net_change": 3500.0,
            },
            {
                "date": "2026-09-15",
                "best": 26800.0,
                "expected": 22100.0,
                "worst": 18450.0,
                "net_change": -12000.0,
            },
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)