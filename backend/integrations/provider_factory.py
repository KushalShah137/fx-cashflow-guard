"""
================================================================================
EXECUTION PROVIDER FACTORY & REGISTRY
================================================================================
Instantiates the appropriate ExecutionProvider (Wise Sandbox vs. Mock Provider)
based on runtime configuration and environment variables.
================================================================================
"""

import os
from typing import Optional
from backend.integrations.provider_interface import (
    ProviderExecutionProtocol,
    ProviderQuote,
    ProviderExecutionResult,
    ProviderStatusResult,
    ProviderError,
    ProviderTimeoutError,
    ProviderAuthError,
)
from backend.integrations.mock_wise_client import MockWiseClient
from backend.integrations.wise_client import WiseClient

# Default singleton instances
_default_mock_provider: Optional[MockWiseClient] = None
_default_wise_provider: Optional[WiseClient] = None


def get_execution_provider(force_mock: Optional[bool] = None) -> ProviderExecutionProtocol:
    """
    Returns the active execution provider instance.
    Uses Wise Sandbox if WISE_API_KEY is configured and not forced to mock.
    """
    global _default_mock_provider, _default_wise_provider

    use_mock = force_mock
    if use_mock is None:
        env_mock = os.getenv("WISE_USE_MOCK", "").lower().strip()
        if env_mock in ("true", "1", "yes"):
            use_mock = True
        else:
            api_key = os.getenv("WISE_API_KEY")
            use_mock = not bool(api_key)

    if use_mock:
        if _default_mock_provider is None:
            _default_mock_provider = MockWiseClient()
        return _default_mock_provider
    else:
        if _default_wise_provider is None:
            _default_wise_provider = WiseClient()
        return _default_wise_provider


def reset_mock_provider() -> None:
    """Resets the mock provider store (useful for tests and demo resets)."""
    global _default_mock_provider
    _default_mock_provider = MockWiseClient()
