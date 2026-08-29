from datetime import date, timedelta
from typing import Dict, List, Any


def convert_currency(amount: float, from_curr: str, to_curr: str, rates: Dict[str, float]) -> float:
    from_curr = from_curr.upper()
    to_curr = to_curr.upper()
    if from_curr == to_curr:
        return amount

    # Base currency in rates is USD: rate means 1 Unit of Currency = X USD
    # USD: 1.0, EUR: 1.08, GBP: 1.28
    rate_from_to_usd = rates.get(from_curr, 1.0)
    rate_to_to_usd = rates.get(to_curr, 1.0)

    amount_in_usd = amount * rate_from_to_usd
    amount_in_target = amount_in_usd / rate_to_to_usd
    return amount_in_target


def calculate_deterministic_forecast(
    data: Dict[str, Any],
    target_currency: str = "USD",
    days: int = 90,
    start_date_str: str = "2026-08-29"
) -> Dict[str, Any]:
    target_currency = target_currency.upper()
    fx_config = data.get("fx_config", {})
    rates = fx_config.get("rates", {"USD": 1.0, "EUR": 1.08, "GBP": 1.28})
    
    # Scale starting balance and danger threshold to requested target currency
    base_starting_balance = float(data.get("starting_balance", 50000.0))
    base_danger_threshold = float(data.get("danger_threshold", 20000.0))
    
    starting_balance = round(convert_currency(base_starting_balance, "USD", target_currency, rates), 2)
    danger_threshold = round(convert_currency(base_danger_threshold, "USD", target_currency, rates), 2)

    transactions = data.get("transactions", [])
    
    # Group transactions by date
    txns_by_date: Dict[str, List[Dict[str, Any]]] = {}
    for txn in transactions:
        t_date = txn.get("date")
        if t_date:
            txns_by_date.setdefault(t_date, []).append(txn)

    start_date = date.fromisoformat(start_date_str)
    current_balance = starting_balance
    forecast_points = []
    breach_dates = []

    for i in range(days):
        day_date = start_date + timedelta(days=i)
        day_str = day_date.isoformat()
        
        # Calculate daily net cashflow in target currency
        day_txns = txns_by_date.get(day_str, [])
        net_change = 0.0
        for txn in day_txns:
            amt = float(txn.get("amount", 0.0))
            txn_curr = txn.get("currency", "USD")
            converted_amt = convert_currency(amt, txn_curr, target_currency, rates)
            net_change += converted_amt

        current_balance += net_change
        expected_balance = round(current_balance, 2)
        net_change_rounded = round(net_change, 2)
        
        # In deterministic step 3, best and worst equal expected
        best_val = expected_balance
        worst_val = expected_balance

        if worst_val < danger_threshold:
            breach_dates.append(day_str)

        forecast_points.append({
            "date": day_str,
            "best": best_val,
            "expected": expected_balance,
            "worst": worst_val,
            "net_change": net_change_rounded
        })

    all_worst = [p["worst"] for p in forecast_points]
    all_best = [p["best"] for p in forecast_points]

    min_worst = min(all_worst) if all_worst else starting_balance
    max_best = max(all_best) if all_best else starting_balance
    final_expected = forecast_points[-1]["expected"] if forecast_points else starting_balance

    return {
        "currency": target_currency,
        "starting_balance": starting_balance,
        "danger_threshold": danger_threshold,
        "has_breach": len(breach_dates) > 0,
        "breach_dates": breach_dates,
        "summary": {
            "min_worst_case": round(min_worst, 2),
            "max_best_case": round(max_best, 2),
            "final_expected": round(final_expected, 2)
        },
        "forecast": forecast_points
    }