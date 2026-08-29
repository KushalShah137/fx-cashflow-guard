"""
================================================================================
WISE PLATFORM SANDBOX API CLIENT & RESILIENT FALLBACK ENGINE
--------------------------------------------------------------------------------
Communicates with the Wise Sandbox (https://api.wise-sandbox.com) to generate
live currency conversion quotes and execute hedging actions. Includes resilient
fallbacks on 401 unauthorized, timeout, network error, and malformed responses.
================================================================================
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import httpx

# Load .env file from project root or backend directory
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

logger = logging.getLogger("wise_api")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

WISE_SANDBOX_BASE_URL = os.getenv("WISE_BASE_URL", "https://api.wise-sandbox.com")

# Fallback indicative market rates for simulation
FALLBACK_INDICATIVE_RATES = {
    "EUR": 1.1582,
    "GBP": 1.3534,
    "INR": 0.0105,
    "CNY": 0.1488,
    "JPY": 0.00626,
    "AUD": 0.7195,
    "USD": 1.0,
}


def _make_resilient_quote(
    source_currency: str,
    target_currency: str,
    source_amount: float,
    status_label: str = "sandbox_simulated",
    note: str = "",
    quote_id: Optional[str] = None,
    rate: Optional[float] = None,
    fee: Optional[float] = None,
    raw_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generates a standardized quote dictionary shape guaranteed to be resilient."""
    src = source_currency.upper().strip()
    tgt = target_currency.upper().strip()
    amt = abs(float(source_amount))

    calc_rate = rate or FALLBACK_INDICATIVE_RATES.get(src, 1.0)
    calc_fee = fee if fee is not None else round(amt * 0.0042, 2)
    qid = quote_id or f"quote_sb_{uuid.uuid4().hex[:12]}"

    return {
        "status": status_label,
        "quote_id": qid,
        "rate": float(calc_rate),
        "fee": float(calc_fee),
        "sourceCurrency": src,
        "targetCurrency": tgt,
        "sourceAmount": amt,
        "targetAmount": round((amt - calc_fee) * calc_rate, 2),
        "note": note or "Wise Sandbox quote processed successfully.",
        "raw": raw_payload or {},
    }


class WiseSandboxClient:
    """
    Client for interacting with Wise Platform Sandbox API.
    Guarantees resilient response shapes across all failure modes (401, timeout, exceptions).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        profile_id: Optional[str] = None,
        base_url: str = WISE_SANDBOX_BASE_URL,
        timeout: float = 5.0,
    ):
        self.api_key = api_key or os.getenv("WISE_API_KEY")
        self.profile_id = profile_id or os.getenv("WISE_PROFILE_ID")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.profile_id)

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def fetch_profiles(self) -> Optional[list]:
        """Fetch profiles associated with the API key if profile_id is not set."""
        if not self.api_key:
            return None
        url = f"{self.base_url}/v2/profiles"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=self.get_headers())
                if res.status_code == 200:
                    return res.json()
                logger.warning("Wise get profiles returned status %d", res.status_code)
        except Exception as e:
            logger.warning("Wise get profiles exception: %s", e)
        return None

    def create_quote(
        self,
        source_currency: str,
        target_currency: str,
        source_amount: float,
    ) -> Dict[str, Any]:
        """
        Creates a Quote in the Wise Sandbox (POST /v3/profiles/{profileId}/quotes).
        Returns guaranteed standardized quote shape even on 401, timeout, or network failure.
        """
        src = source_currency.upper().strip()
        tgt = target_currency.upper().strip()
        amt = abs(float(source_amount))

        # Auto-discover profile_id if key exists
        if not self.profile_id and self.api_key:
            profiles = self.fetch_profiles()
            if profiles and isinstance(profiles, list) and len(profiles) > 0:
                self.profile_id = str(profiles[0].get("id"))
                logger.info("Discovered Wise profile ID: %s", self.profile_id)

        if not self.is_configured:
            logger.info(
                "Wise credentials unconfigured or running in offline mode. Generating standardized simulated quote."
            )
            return _make_resilient_quote(
                source_currency=src,
                target_currency=tgt,
                source_amount=amt,
                status_label="simulated",
                note="Credentials not set — local indicative quote executed cleanly.",
            )

        url = f"{self.base_url}/v3/profiles/{self.profile_id}/quotes"
        payload = {
            "sourceCurrency": src,
            "targetCurrency": tgt,
            "sourceAmount": amt,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=self.get_headers(), json=payload)
                if response.status_code in (200, 201):
                    try:
                        data = response.json()
                        logger.info(
                            "Wise Sandbox Quote created successfully: id=%s, rate=%s",
                            data.get("id"),
                            data.get("rate"),
                        )
                        return _make_resilient_quote(
                            source_currency=src,
                            target_currency=tgt,
                            source_amount=amt,
                            status_label="sandbox_success",
                            note="Wise Sandbox live API quote generated successfully.",
                            quote_id=data.get("id"),
                            rate=float(data.get("rate", 1.0)),
                            fee=float(data.get("fee", 0.0)),
                            raw_payload=data,
                        )
                    except Exception as json_err:
                        logger.warning("Wise returned invalid JSON payload: %s", json_err)
                        return _make_resilient_quote(
                            source_currency=src,
                            target_currency=tgt,
                            source_amount=amt,
                            status_label="sandbox_fallback_malformed_json",
                            note="Received malformed JSON from Wise; fallback quote applied.",
                        )
                elif response.status_code in (401, 403):
                    logger.warning("Wise Sandbox authentication failed (%d). Using fallback quote.", response.status_code)
                    return _make_resilient_quote(
                        source_currency=src,
                        target_currency=tgt,
                        source_amount=amt,
                        status_label="sandbox_auth_fallback",
                        note=f"Wise authentication returned {response.status_code}; simulated quote applied.",
                    )
                else:
                    logger.warning("Wise Sandbox returned HTTP %d. Using fallback quote.", response.status_code)
                    return _make_resilient_quote(
                        source_currency=src,
                        target_currency=tgt,
                        source_amount=amt,
                        status_label="sandbox_http_fallback",
                        note=f"Wise returned HTTP {response.status_code}; simulated quote applied.",
                    )
        except httpx.TimeoutException:
            logger.warning("Wise Sandbox request timed out after %.1fs. Using fallback quote.", self.timeout)
            return _make_resilient_quote(
                source_currency=src,
                target_currency=tgt,
                source_amount=amt,
                status_label="sandbox_timeout_fallback",
                note=f"Wise connection timed out after {self.timeout}s; simulated quote applied.",
            )
        except Exception as e:
            logger.warning("Wise Sandbox request failed (%s). Using fallback quote.", e)
            return _make_resilient_quote(
                source_currency=src,
                target_currency=tgt,
                source_amount=amt,
                status_label="sandbox_exception_fallback",
                note=f"Wise connection error ({type(e).__name__}); simulated quote applied.",
            )


# Default client instance
wise_client = WiseSandboxClient()


def execute_wise_action(
    action: str,
    currency: str,
    amount: float,
    base_currency: str = "USD",
) -> Dict[str, Any]:
    """
    High-level trigger called when an action (convert_and_hold / settle_now) is executed.
    """
    logger.info("Triggering Wise Sandbox action: %s for %s %.2f", action, currency, amount)
    return wise_client.create_quote(
        source_currency=currency,
        target_currency=base_currency,
        source_amount=amount,
    )