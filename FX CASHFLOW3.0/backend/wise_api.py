import os
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


class WiseSandboxClient:
    """
    Client for interacting with Wise Platform Sandbox API.
    Provides fallback simulation if credentials are unset or if sandbox fails/times out.
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
                logger.warning("Wise get profiles failed with status %d: %s", res.status_code, res.text)
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
        Returns the quote object or fallback simulated quote if API call fails.
        """
        source_currency = source_currency.upper().strip()
        target_currency = target_currency.upper().strip()

        # If profile_id is missing but api_key is present, attempt auto-discovery
        if not self.profile_id and self.api_key:
            profiles = self.fetch_profiles()
            if profiles and isinstance(profiles, list) and len(profiles) > 0:
                self.profile_id = str(profiles[0].get("id"))
                logger.info("Discovered Wise profile ID: %s", self.profile_id)

        if not self.is_configured:
            logger.warning(
                "Wise API credentials not fully configured (WISE_API_KEY or WISE_PROFILE_ID missing). "
                "Falling back to graceful simulation."
            )
            return {
                "status": "simulated",
                "sourceCurrency": source_currency,
                "targetCurrency": target_currency,
                "sourceAmount": source_amount,
                "note": "Credentials not configured — local fallback quote executed successfully.",
            }

        url = f"{self.base_url}/v3/profiles/{self.profile_id}/quotes"
        payload = {
            "sourceCurrency": source_currency,
            "targetCurrency": target_currency,
            "sourceAmount": abs(float(source_amount)),
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=self.get_headers(), json=payload)
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(
                        "Wise Sandbox Quote created successfully: id=%s, rate=%s",
                        data.get("id"),
                        data.get("rate"),
                    )
                    return {
                        "status": "sandbox_success",
                        "quote_id": data.get("id"),
                        "rate": data.get("rate"),
                        "fee": data.get("fee"),
                        "estimatedDelivery": data.get("estimatedDelivery"),
                        "raw": data,
                    }
                else:
                    logger.warning(
                        "Wise Sandbox API returned status %d: %s. Falling back to local ledger update.",
                        response.status_code,
                        response.text,
                    )
                    return {
                        "status": "sandbox_error_fallback",
                        "status_code": response.status_code,
                        "error": response.text,
                    }
        except Exception as e:
            logger.warning("Wise Sandbox API request failed (%s). Falling back to local ledger.", e)
            return {
                "status": "exception_fallback",
                "error": str(e),
            }


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