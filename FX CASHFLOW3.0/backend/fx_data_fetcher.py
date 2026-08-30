"""
================================================================================
FRANKFURTER.DEV FX DATA FETCHER & HISTORICAL CACHE REFRESHER
--------------------------------------------------------------------------------
Fetches real daily historical foreign exchange rates from Frankfurter.dev
(European Central Bank reference data) and maintains data/fx_historical_cache.json.
Supported Currencies: USD (base), EUR, GBP, INR, CNY, JPY, AUD.
================================================================================
"""

import argparse
import json
import logging
import math
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import requests

# Configure logging
logger = logging.getLogger("fx_data_fetcher")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"
DEFAULT_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "fx_historical_cache.json"
DEFAULT_SYMBOLS = ["EUR", "GBP", "INR", "CNY", "JPY", "AUD"]


def fetch_historical_rates(
    base: str = "USD",
    symbols: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timeout: float = 15.0,
) -> List[Dict[str, Any]]:
    """
    Fetches daily historical FX rates from Frankfurter.dev for given date range.

    Args:
        base: Base currency (default: USD).
        symbols: Foreign currencies to fetch (default: ["EUR", "GBP", "INR", "CNY", "JPY", "AUD"]).
        start_date: Start date string (YYYY-MM-DD). Defaults to 2 years ago.
        end_date: End date string (YYYY-MM-DD). Defaults to today.
        timeout: HTTP request timeout in seconds.

    Returns:
        List of dicts: [{"date": "YYYY-MM-DD", "EUR": 0.85889, "GBP": 0.73624, ...}, ...]
        sorted chronologically ascending.
    """
    if symbols is None:
        symbols = list(DEFAULT_SYMBOLS)
    
    symbols_upper = [s.upper().strip() for s in symbols]
    base_upper = base.upper().strip()

    today = date.today()
    if not end_date:
        end_date = today.isoformat()
    if not start_date:
        start_date = (today - timedelta(days=730)).isoformat()

    symbols_param = ",".join(symbols_upper)
    url = f"{FRANKFURTER_BASE_URL}/{start_date}..{end_date}?base={base_upper}&symbols={symbols_param}"
    logger.info("Fetching FX data from Frankfurter.dev: %s", url)

    response = requests.get(url, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(
            f"Frankfurter API returned status {response.status_code}: {response.text}"
        )

    data = response.json()
    raw_rates = data.get("rates", {})
    if not raw_rates:
        raise ValueError("Frankfurter API returned an empty rates object.")

    # Parse and sort chronologically
    sorted_dates = sorted(raw_rates.keys())
    historical_rates: List[Dict[str, Any]] = []

    for dt in sorted_dates:
        day_rates = raw_rates[dt]
        # Verify all requested symbols are present and positive
        if all(sym in day_rates and isinstance(day_rates[sym], (int, float)) and day_rates[sym] > 0 for sym in symbols_upper):
            entry: Dict[str, Any] = {"date": dt}
            for sym in symbols_upper:
                entry[sym] = round(float(day_rates[sym]), 5)
            historical_rates.append(entry)

    if not historical_rates:
        raise ValueError("No valid aligned FX rate records found in API response.")

    return historical_rates


def fetch_latest_spot_rates(
    base: str = "USD",
    symbols: Optional[List[str]] = None,
    timeout: float = 10.0,
) -> Dict[str, float]:
    """
    Fetches the latest spot rate from Frankfurter.dev.
    """
    if symbols is None:
        symbols = list(DEFAULT_SYMBOLS)
    
    symbols_upper = [s.upper().strip() for s in symbols]
    base_upper = base.upper().strip()
    symbols_param = ",".join(symbols_upper)

    url = f"{FRANKFURTER_BASE_URL}/latest?base={base_upper}&symbols={symbols_param}"
    response = requests.get(url, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"Frankfurter latest API returned status {response.status_code}")

    data = response.json()
    rates = data.get("rates", {})
    return {sym: float(rates[sym]) for sym in symbols_upper if sym in rates}


def refresh_fx_cache(
    cache_path: Optional[Path] = None,
    base: str = "USD",
    symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Refreshes data/fx_historical_cache.json with live 2-year data from Frankfurter.dev.
    Gracefully leaves existing cache untouched if fetch fails.
    """
    target_path = cache_path or DEFAULT_CACHE_PATH
    if symbols is None:
        symbols = list(DEFAULT_SYMBOLS)

    try:
        rates = fetch_historical_rates(base=base, symbols=symbols)
        actual_start = rates[0]["date"]
        actual_end = rates[-1]["date"]

        cache_data = {
            "description": "Frankfurter.dev historical daily FX rates cache (USD base). Rates represent units of currency per 1 USD.",
            "base_currency": base.upper(),
            "start_date": actual_start,
            "end_date": actual_end,
            "currencies": symbols,
            "historical_rates": rates,
        }

        # Safe write
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)

        logger.info(
            "Successfully refreshed FX historical cache at %s (%d rows: %s to %s)",
            target_path,
            len(rates),
            actual_start,
            actual_end,
        )
        return cache_data

    except Exception as e:
        logger.warning(
            "Failed to refresh FX cache from Frankfurter.dev: %s. Existing cache was preserved.",
            e,
        )
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        raise


def compute_volatility_metrics(cache_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Computes daily log returns and annualized volatility metrics from cache for all currencies.
    """
    target_path = cache_path or DEFAULT_CACHE_PATH
    with open(target_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    rates_list = data.get("historical_rates", [])
    currencies = data.get("currencies", DEFAULT_SYMBOLS)

    metrics: Dict[str, Any] = {}
    for ccy in currencies:
        series = [r[ccy] for r in rates_list if ccy in r and r[ccy] > 0]
        if len(series) > 2:
            log_returns = np.diff(np.log(np.array(series, dtype=np.float64)))
            daily_vol = float(np.std(log_returns))
            annualized_vol = daily_vol * math.sqrt(252)
            metrics[ccy] = {
                "observations": len(series),
                "daily_volatility": daily_vol,
                "annualized_volatility": annualized_vol,
                "latest_spot_rate": series[-1],
            }
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Frankfurter.dev FX historical data refresher")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch latest 2-year FX history and update data/fx_historical_cache.json",
    )
    args = parser.parse_args()

    if args.refresh or len(sys.argv) == 1:
        print("=" * 70)
        print("FRANKFURTER.DEV FX DATA REFRESH (6 CURRENCIES)")
        print("=" * 70)
        cache_data = refresh_fx_cache()
        rates = cache_data.get("historical_rates", [])
        start_date = cache_data.get("start_date")
        end_date = cache_data.get("end_date")
        row_count = len(rates)

        print(f"Status: SUCCESS")
        print(f"Row Count: {row_count} daily observations")
        print(f"Date Range: {start_date} to {end_date}")
        print(f"Base Currency: {cache_data.get('base_currency')}")
        print(f"Currencies: {', '.join(cache_data.get('currencies', []))}")
        print("-" * 70)
        print("HISTORICAL VOLATILITY & SPOT RATES (252-day annualized):")

        vols = compute_volatility_metrics()
        for ccy, m in vols.items():
            print(
                f"  - {ccy:<4}: Latest Spot = {m['latest_spot_rate']:<10.5f} (1 USD = {m['latest_spot_rate']:.5f} {ccy}), "
                f"Daily Vol = {m['daily_volatility']:.5f} ({m['daily_volatility']*100:.3f}%), "
                f"Annualized Vol = {m['annualized_volatility']:.4f} ({m['annualized_volatility']*100:.2f}%)"
            )
        print("=" * 70)


if __name__ == "__main__":
    main()
