"""
================================================================================
FX NETTING ENGINE
--------------------------------------------------------------------------------
Computes portfolio-level netting opportunities, unnecessary conversion offsets,
avoided conversion fees, and risk reduction across currencies.
================================================================================
"""

import logging
from collections import defaultdict
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("netting_engine")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


class NettingEngine:
    """
    Calculates natural netting offsets across multiple foreign currency exposures.
    """

    def __init__(self, default_fee_rate: float = 0.005):
        """
        Args:
            default_fee_rate: Conversion fee percentage (default: 0.5% / 0.005).
        """
        self.default_fee_rate = default_fee_rate

    def calculate_netting(
        self,
        transactions: List[Any],
        fx_rates: Dict[str, float],
        base_currency: str = "USD",
        anchor_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Groups pending transactions and calculates gross, net, and netting offsets.
        
        Args:
            transactions: List of Transaction objects or dictionaries.
            fx_rates: Active exchange rates dictionary.
            base_currency: Platform base currency (default: USD).
            anchor_date: Forecast start date (default: today).
        """
        if anchor_date is None:
            anchor_date = date.today()

        def _get_field(obj: Any, name: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # Group transactions by currency
        ccy_groups = defaultdict(list)
        for tx in transactions:
            # Normalize dict vs object
            tx_status = _get_field(tx, "status")
            if hasattr(tx_status, "value"):
                tx_status = tx_status.value
            if tx_status != "pending":
                continue
                
            tx_ccy = _get_field(tx, "currency")
            if hasattr(tx_ccy, "value"):
                tx_ccy = tx_ccy.value
            if tx_ccy == base_currency:
                continue
                
            ccy_groups[tx_ccy].append(tx)

        portfolio_summary = {}
        total_fees_avoided_base = 0.0
        total_unnecessary_conversion_base = 0.0
        total_risk_reduction_base = 0.0

        for ccy, txs in ccy_groups.items():
            rate = fx_rates.get(ccy, 1.0)
            
            gross_payables = 0.0
            gross_receivables = 0.0
            near_term_exposure = 0.0
            
            # Perfect netting groups (same-day offsets)
            daily_inflows = defaultdict(float)
            daily_outflows = defaultdict(float)

            for tx in txs:
                tx_amt = _get_field(tx, "amount", 0.0)
                tx_dir = _get_field(tx, "direction")
                if hasattr(tx_dir, "value"):
                    tx_dir = tx_dir.value
                tx_date_raw = _get_field(tx, "date")
                
                # Parse date
                if isinstance(tx_date_raw, str):
                    tx_date = datetime.strptime(tx_date_raw, "%Y-%m-%d").date()
                else:
                    tx_date = tx_date_raw

                days_to_due = (tx_date - anchor_date).days

                if tx_dir == "receivable":
                    gross_receivables += tx_amt
                    daily_inflows[tx_date] += tx_amt
                    if 0 <= days_to_due <= 30:
                        near_term_exposure += tx_amt
                else:
                    gross_payables += tx_amt
                    daily_outflows[tx_date] += tx_amt
                    if 0 <= days_to_due <= 30:
                        near_term_exposure -= tx_amt

            net_exposure = gross_receivables - gross_payables
            
            # Portfolio-level (horizon) netting potential
            unnecessary_conversion = min(gross_receivables, gross_payables)
            fees_avoided = unnecessary_conversion * self.default_fee_rate
            
            # Perfect same-day netting calculation
            perfect_netting_volume = 0.0
            all_dates = set(daily_inflows.keys()) | set(daily_outflows.keys())
            for d in all_dates:
                perfect_netting_volume += min(daily_inflows[d], daily_outflows[d])

            # Convert to base currency (USD)
            # Spot rate represents units of foreign currency per 1 USD (e.g. 0.85 EUR per 1 USD)
            # So base_amount = foreign_amount / rate
            gross_payables_base = gross_payables / rate
            gross_receivables_base = gross_receivables / rate
            net_exposure_base = net_exposure / rate
            near_term_exposure_base = near_term_exposure / rate
            
            unnecessary_conversion_base = unnecessary_conversion / rate
            fees_avoided_base = fees_avoided / rate
            perfect_netting_base = perfect_netting_volume / rate
            
            # Risk reduction: gross volume exposed vs. netted remaining exposure
            gross_exposure_volume = gross_receivables + gross_payables
            netted_exposure_volume = abs(net_exposure)
            risk_reduction_volume = gross_exposure_volume - netted_exposure_volume
            risk_reduction_base = risk_reduction_volume / rate

            portfolio_summary[ccy] = {
                "currency": ccy,
                "gross_receivables": round(gross_receivables, 2),
                "gross_payables": round(gross_payables, 2),
                "net_exposure": round(net_exposure, 2),
                "near_term_exposure": round(near_term_exposure, 2),
                "gross_receivables_base": round(gross_receivables_base, 2),
                "gross_payables_base": round(gross_payables_base, 2),
                "net_exposure_base": round(net_exposure_base, 2),
                "near_term_exposure_base": round(near_term_exposure_base, 2),
                "unnecessary_conversion_amount": round(unnecessary_conversion, 2),
                "unnecessary_conversion_base": round(unnecessary_conversion_base, 2),
                "perfect_same_day_netting": round(perfect_netting_volume, 2),
                "perfect_same_day_netting_base": round(perfect_netting_base, 2),
                "estimated_fees_avoided": round(fees_avoided, 2),
                "estimated_fees_avoided_base": round(fees_avoided_base, 2),
                "estimated_risk_reduction": round(risk_reduction_volume, 2),
                "estimated_risk_reduction_base": round(risk_reduction_base, 2),
                "hedgeable_exposure": round(net_exposure, 2),
            }

            total_fees_avoided_base += fees_avoided_base
            total_unnecessary_conversion_base += unnecessary_conversion_base
            total_risk_reduction_base += risk_reduction_base

        return {
            "portfolio": portfolio_summary,
            "totals": {
                "base_currency": base_currency,
                "total_unnecessary_conversion_base": round(total_unnecessary_conversion_base, 2),
                "total_fees_avoided_base": round(total_fees_avoided_base, 2),
                "total_risk_reduction_base": round(total_risk_reduction_base, 2),
            }
        }
