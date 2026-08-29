"""
================================================================================
EXECUTION PROVIDER INTERFACE & NORMALIZED PROTOCOL
================================================================================
Defines the abstract interface for currency quote and money-movement execution
providers (e.g. Wise Platform Sandbox vs. Deterministic Mock Provider).
================================================================================
"""

from typing import Protocol, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ProviderQuote:
    quote_id: str
    source_currency: str
    target_currency: str
    source_amount: float
    target_amount: float
    rate: float
    fee: float
    delivery_estimate: str
    provider: str
    created_at: str
    expires_at: str
    raw_payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quote_id": self.quote_id,
            "source_currency": self.source_currency,
            "target_currency": self.target_currency,
            "source_amount": self.source_amount,
            "target_amount": self.target_amount,
            "rate": self.rate,
            "fee": self.fee,
            "delivery_estimate": self.delivery_estimate,
            "provider": self.provider,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "raw_payload": self.raw_payload,
        }


@dataclass
class ProviderExecutionResult:
    status: str  # "SUCCESS", "FAILED", "TIMEOUT", "REQUIRES_REVIEW"
    provider: str
    provider_reference: Optional[str]
    quote_id: str
    idempotency_key: str
    source_currency: str
    target_currency: str
    source_amount: float
    target_amount: float
    rate: float
    fee: float
    executed_at: str
    error_message: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "provider_reference": self.provider_reference,
            "quote_id": self.quote_id,
            "idempotency_key": self.idempotency_key,
            "source_currency": self.source_currency,
            "target_currency": self.target_currency,
            "source_amount": self.source_amount,
            "target_amount": self.target_amount,
            "rate": self.rate,
            "fee": self.fee,
            "executed_at": self.executed_at,
            "error_message": self.error_message,
            "raw_payload": self.raw_payload or {},
        }


@dataclass
class ProviderStatusResult:
    provider_reference: str
    status: str  # "COMPLETED", "PROCESSING", "FAILED", "UNKNOWN"
    provider: str
    source_currency: str
    target_currency: str
    source_amount: float
    target_amount: float
    verified: bool
    details: Dict[str, Any]


class ProviderError(Exception):
    """Base exception for provider-level failures."""
    def __init__(self, message: str, code: str = "PROVIDER_ERROR", retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ProviderTimeoutError(ProviderError):
    """Raised when a provider request times out without confirmation."""
    def __init__(self, message: str = "Provider connection timed out."):
        super().__init__(message, code="PROVIDER_TIMEOUT", retryable=False)


class ProviderAuthError(ProviderError):
    """Raised when authentication credentials fail."""
    def __init__(self, message: str = "Provider authentication failed."):
        super().__init__(message, code="PROVIDER_AUTH_ERROR", retryable=False)


class ProviderExecutionProtocol(Protocol):
    """Abstract protocol implemented by all execution providers."""

    @property
    def provider_name(self) -> str:
        ...

    def create_quote(
        self,
        source_currency: str,
        target_currency: str,
        source_amount: float,
        expiry_seconds: int = 600,
    ) -> ProviderQuote:
        ...

    def get_quote(self, quote_id: str) -> Optional[ProviderQuote]:
        ...

    def execute_quote(
        self,
        quote: ProviderQuote,
        idempotency_key: str,
        action_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProviderExecutionResult:
        ...

    def get_execution_status(
        self,
        provider_reference: str,
        idempotency_key: Optional[str] = None,
    ) -> ProviderStatusResult:
        ...
