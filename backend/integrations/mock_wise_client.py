"""
================================================================================
DETERMINISTIC MOCK WISE EXECUTION PROVIDER
================================================================================
Implements ProviderExecutionProtocol with full realistic financial lifecycle
behavior: quote creation, quote expiry enforcement, idempotency, realistic fees,
and configurable testing hooks (simulated timeout, failure, mismatch).
================================================================================
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from backend.integrations.provider_interface import (
    ProviderQuote,
    ProviderExecutionResult,
    ProviderStatusResult,
    ProviderTimeoutError,
    ProviderError,
)

MOCK_SPOT_RATES = {
    ("EUR", "USD"): 1.1643,
    ("USD", "EUR"): 0.8589,
    ("GBP", "USD"): 1.3582,
    ("USD", "GBP"): 0.7362,
    ("INR", "USD"): 0.01048,
    ("USD", "INR"): 95.39,
    ("CNY", "USD"): 0.14879,
    ("USD", "CNY"): 6.7209,
    ("JPY", "USD"): 0.00626,
    ("USD", "JPY"): 159.68,
    ("AUD", "USD"): 0.71948,
    ("USD", "AUD"): 1.3899,
}


class MockWiseClient:
    """Deterministic Mock Execution Provider for tests and offline demonstrations."""

    def __init__(self, fee_percentage: float = 0.0042):
        self.fee_percentage = fee_percentage
        self._quotes: Dict[str, ProviderQuote] = {}
        self._executions_by_idempotency: Dict[str, ProviderExecutionResult] = {}
        self._executions_by_ref: Dict[str, ProviderExecutionResult] = {}

        # Testing hooks
        self.simulate_timeout: bool = False
        self.simulate_failure: bool = False
        self.simulate_verification_mismatch: bool = False

    @property
    def provider_name(self) -> str:
        return "MOCK_WISE_PROVIDER"

    def _resolve_rate(self, source: str, target: str) -> float:
        src = source.upper().strip()
        tgt = target.upper().strip()
        if src == tgt:
            return 1.0
        if (src, tgt) in MOCK_SPOT_RATES:
            return MOCK_SPOT_RATES[(src, tgt)]
        if (tgt, src) in MOCK_SPOT_RATES:
            return 1.0 / MOCK_SPOT_RATES[(tgt, src)]
        return 1.0

    def create_quote(
        self,
        source_currency: str,
        target_currency: str,
        source_amount: float,
        expiry_seconds: int = 600,
    ) -> ProviderQuote:
        src = source_currency.upper().strip()
        tgt = target_currency.upper().strip()
        amt = abs(float(source_amount))

        rate = self._resolve_rate(src, tgt)
        fee = round(amt * self.fee_percentage, 2)
        target_amount = round((amt - fee) * rate, 2)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=expiry_seconds)
        quote_id = f"mock_quote_{uuid.uuid4().hex[:12]}"

        quote = ProviderQuote(
            quote_id=quote_id,
            source_currency=src,
            target_currency=tgt,
            source_amount=amt,
            target_amount=target_amount,
            rate=rate,
            fee=fee,
            delivery_estimate="Within 2 hours",
            provider=self.provider_name,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            raw_payload={
                "mock": True,
                "quote_id": quote_id,
                "rate": rate,
                "fee": fee,
                "sourceAmount": amt,
                "targetAmount": target_amount,
            },
        )
        self._quotes[quote_id] = quote
        return quote

    def get_quote(self, quote_id: str) -> Optional[ProviderQuote]:
        return self._quotes.get(quote_id)

    def execute_quote(
        self,
        quote: ProviderQuote,
        idempotency_key: str,
        action_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProviderExecutionResult:
        # 1. Idempotency Check: Return existing execution if already processed
        if idempotency_key in self._executions_by_idempotency:
            return self._executions_by_idempotency[idempotency_key]

        # 2. Testing Hook: Simulate Timeout
        if self.simulate_timeout:
            raise ProviderTimeoutError("Simulated mock provider network timeout during execution.")

        # 3. Testing Hook: Simulate Failure
        if self.simulate_failure:
            raise ProviderError("Simulated mock provider execution rejection.", code="MOCK_EXECUTION_REJECTED")

        now_str = datetime.now(timezone.utc).isoformat()
        provider_ref = f"mock_tx_{uuid.uuid4().hex[:16]}"

        if self.simulate_verification_mismatch:
            # Return mismatched source currency and amount for verification failure testing
            result = ProviderExecutionResult(
                status="SUCCESS",
                provider=self.provider_name,
                provider_reference=provider_ref,
                quote_id=quote.quote_id,
                idempotency_key=idempotency_key,
                source_currency="MISMATCHED_CCY",
                target_currency=quote.target_currency,
                source_amount=quote.source_amount * 2.0,
                target_amount=quote.target_amount,
                rate=quote.rate,
                fee=quote.fee,
                executed_at=now_str,
                error_message=None,
                raw_payload={"mock_mismatch": True},
            )
            self._executions_by_idempotency[idempotency_key] = result
            self._executions_by_ref[provider_ref] = result
            return result

        result = ProviderExecutionResult(
            status="SUCCESS",
            provider=self.provider_name,
            provider_reference=provider_ref,
            quote_id=quote.quote_id,
            idempotency_key=idempotency_key,
            source_currency=quote.source_currency,
            target_currency=quote.target_currency,
            source_amount=quote.source_amount,
            target_amount=quote.target_amount,
            rate=quote.rate,
            fee=quote.fee,
            executed_at=now_str,
            error_message=None,
            raw_payload={
                "mock_execution": True,
                "provider_reference": provider_ref,
                "action_type": action_type,
                "metadata": metadata or {},
            },
        )

        self._executions_by_idempotency[idempotency_key] = result
        self._executions_by_ref[provider_ref] = result
        return result

    def get_execution_status(
        self,
        provider_reference: str,
        idempotency_key: Optional[str] = None,
    ) -> ProviderStatusResult:
        exec_res = None
        if provider_reference in self._executions_by_ref:
            exec_res = self._executions_by_ref[provider_reference]
        elif idempotency_key and idempotency_key in self._executions_by_idempotency:
            exec_res = self._executions_by_idempotency[idempotency_key]

        if not exec_res:
            return ProviderStatusResult(
                provider_reference=provider_reference,
                status="UNKNOWN",
                provider=self.provider_name,
                source_currency="",
                target_currency="",
                source_amount=0.0,
                target_amount=0.0,
                verified=False,
                details={"error": "Reference not found in mock store."},
            )

        if self.simulate_verification_mismatch:
            # Return mismatched currency or amount for testing verification failure
            return ProviderStatusResult(
                provider_reference=provider_reference,
                status="COMPLETED",
                provider=self.provider_name,
                source_currency="MISMATCHED_CCY",
                target_currency=exec_res.target_currency,
                source_amount=exec_res.source_amount * 2,
                target_amount=exec_res.target_amount,
                verified=False,
                details={"warning": "Simulated mismatch."},
            )

        return ProviderStatusResult(
            provider_reference=provider_reference,
            status="COMPLETED",
            provider=self.provider_name,
            source_currency=exec_res.source_currency,
            target_currency=exec_res.target_currency,
            source_amount=exec_res.source_amount,
            target_amount=exec_res.target_amount,
            verified=True,
            details=exec_res.raw_payload or {},
        )
