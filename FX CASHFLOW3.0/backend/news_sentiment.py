"""
================================================================================
NEWS SENTIMENT LAYER (ISOLATED)
--------------------------------------------------------------------------------
Fetches live FX news from Finnhub, extracts macroeconomic sentiment & volatility
multipliers using local Qwen2.5 via Ollama, and writes an atomic sentiment cache.
================================================================================
"""

import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, field_validator

# Load environment variables from .env if present
load_dotenv()

logger = logging.getLogger("news_sentiment")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

# Currency keyword match dictionary (case-insensitive)
KEYWORD_MAP: Dict[str, List[str]] = {
    "EUR": ["EUR", "euro", "ECB", "Lagarde", "Eurozone"],
    "GBP": ["GBP", "pound", "sterling", "BoE", "Bank of England", "Bailey"],
    "USD": ["USD", "dollar", "Fed", "Federal Reserve", "Powell", "Treasury", "Bessent"],
    "INR": ["INR", "rupee", "RBI", "Reserve Bank of India", "India"],
    "CNY": ["CNY", "yuan", "renminbi", "PBOC", "China", "Beijing"],
    "JPY": ["JPY", "yen", "BoJ", "Bank of Japan", "Ueda", "Tokyo"],
    "AUD": ["AUD", "aussie", "RBA", "Reserve Bank of Australia", "Australia"],
}

FALLBACK: Dict[str, Any] = {
    "raw": {
        "sentiment_score": 0.0,
        "volatility_multiplier": 1.0,
        "drift_bias_bps": 0.0,
        "confidence": 0.0,
    },
    "effective": {
        "drift_bias_bps": 0.0,
        "volatility_multiplier": 1.0,
    },
    "headline_count": 0,
    "headlines": [],
    "source": "fallback",
}


class NewsSentiment(BaseModel):
    currency: str
    sentiment_score: float  # -1.0 to 1.0
    volatility_multiplier: float  # e.g. 1.0 = no change, 1.4 = +40% vol
    drift_bias_bps: float  # basis points, can be negative
    confidence: float  # 0.0 to 1.0

    @field_validator("sentiment_score")
    @classmethod
    def validate_sentiment_score(cls, v: float) -> float:
        if not (-1.0 <= v <= 1.0):
            raise ValueError("sentiment_score must be between -1.0 and 1.0")
        return v

    @field_validator("volatility_multiplier")
    @classmethod
    def validate_volatility_multiplier(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("volatility_multiplier must be non-negative")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


def compute_effective_metrics(
    raw_drift_bias_bps: float,
    raw_volatility_multiplier: float,
    confidence: float,
) -> Dict[str, float]:
    """Applies confidence scaling to raw drift bias and volatility multiplier."""
    conf = max(0.0, min(1.0, float(confidence)))
    effective_drift = float(raw_drift_bias_bps) * conf
    effective_vol = 1.0 + (float(raw_volatility_multiplier) - 1.0) * conf
    return {
        "drift_bias_bps": round(effective_drift, 4),
        "volatility_multiplier": round(effective_vol, 4),
    }


def fetch_fx_news(currency: str) -> List[str]:
    """
    Fetches forex and macro market news from Finnhub and filters by currency-specific keywords.
    Never raises an exception — returns [] on any failure.
    """
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        logger.warning("FINNHUB_API_KEY is not configured in environment/.env.")
        return []

    url = "https://finnhub.io/api/v1/news"
    keywords = KEYWORD_MAP.get(currency.upper(), [currency.upper()])

    try:
        all_articles = []
        for cat in ("forex", "general"):
            try:
                resp = requests.get(url, params={"category": cat, "token": api_key}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        all_articles.extend(data)
            except Exception as cat_err:
                logger.warning("Finnhub category %s fetch error: %s", cat, cat_err)

        matched_headlines: List[str] = []
        for item in all_articles:
            if not isinstance(item, dict):
                continue
            headline = item.get("headline", "")
            summary = item.get("summary", "")
            content_lower = f"{headline} {summary}".lower()

            # Check if any keyword matches
            if any(kw.lower() in content_lower for kw in keywords):
                if headline and headline not in matched_headlines:
                    matched_headlines.append(headline)

        logger.info(
            "Fetched %d matched headlines for %s from Finnhub.",
            len(matched_headlines),
            currency,
        )
        return matched_headlines

    except Exception as e:
        logger.warning("Failed to fetch news from Finnhub for %s: %s", currency, e)
        return []


def extract_sentiment(
    currency: str,
    headlines: List[str],
    ollama_base_url: str = "http://localhost:11434/v1",
    model: str = "qwen2.5:7b-instruct",
) -> Dict[str, Any]:
    """
    Batches all headlines into one prompt and calls local Qwen2.5 via Ollama.
    Validates output with Pydantic and returns structured raw + effective metrics.
    Never raises an exception — falls back gracefully on any error.
    """
    if not headlines:
        fb = FALLBACK.copy()
        fb["headlines"] = []
        fb["headline_count"] = 0
        return fb

    prompt_content = (
        f"You are a quantitative FX market analyst. Analyze the following {len(headlines)} "
        f"news headlines for the currency '{currency}'. Weigh all headlines together to form "
        f"one aggregate assessment.\n\n"
        f"Headlines:\n" + "\n".join(f"- {h}" for h in headlines) + "\n\n"
        f"Return ONLY a JSON object matching this schema:\n"
        f"{{\n"
        f'  "currency": "{currency}",\n'
        f'  "sentiment_score": <float between -1.0 (very bearish) and 1.0 (very bullish)>,\n'
        f'  "volatility_multiplier": <float, 1.0 means baseline/normal, >1.0 means elevated market volatility>,\n'
        f'  "drift_bias_bps": <float, expected daily drift in basis points, positive or negative>,\n'
        f'  "confidence": <float between 0.0 and 1.0 indicating signal certainty>\n'
        f"}}"
    )

    try:
        client = OpenAI(base_url=ollama_base_url, api_key="ollama")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert FX risk analyzer. Weigh ALL provided headlines "
                        "together and emit a single balanced JSON object without markdown or formatting."
                    ),
                },
                {"role": "user", "content": prompt_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=30.0,
        )

        content = response.choices[0].message.content
        if not content:
            logger.warning("Ollama returned empty message content for %s.", currency)
            fb = FALLBACK.copy()
            fb["headlines"] = headlines
            fb["headline_count"] = len(headlines)
            return fb

        # Parse and validate with Pydantic
        parsed_data = json.loads(content)
        sentiment_obj = NewsSentiment.model_validate(parsed_data)

        # Compute confidence scaling
        effective = compute_effective_metrics(
            sentiment_obj.drift_bias_bps,
            sentiment_obj.volatility_multiplier,
            sentiment_obj.confidence,
        )

        return {
            "raw": {
                "sentiment_score": round(sentiment_obj.sentiment_score, 4),
                "volatility_multiplier": round(sentiment_obj.volatility_multiplier, 4),
                "drift_bias_bps": round(sentiment_obj.drift_bias_bps, 4),
                "confidence": round(sentiment_obj.confidence, 4),
            },
            "effective": effective,
            "headline_count": len(headlines),
            "headlines": headlines,
            "source": "live",
        }

    except Exception as e:
        logger.warning(
            "Sentiment extraction failed for %s (%s). Using fallback.", currency, e
        )
        fb = FALLBACK.copy()
        fb["headlines"] = headlines
        fb["headline_count"] = len(headlines)
        return fb


def refresh_news_cache(
    currencies: Optional[List[str]] = None,
    output_path: str = "data/news_sentiment_cache.json",
    ollama_base_url: str = "http://localhost:11434/v1",
    model: str = "qwen2.5:7b-instruct",
) -> Dict[str, Any]:
    """
    Fetches news, extracts sentiment, and atomically writes results to JSON cache.
    """
    if currencies is None:
        currencies = ["EUR", "GBP", "USD", "INR", "CNY", "JPY", "AUD"]

    results: Dict[str, Any] = {}
    for ccy in currencies:
        headlines = fetch_fx_news(ccy)
        data = extract_sentiment(
            currency=ccy,
            headlines=headlines,
            ollama_base_url=ollama_base_url,
            model=model,
        )
        results[ccy] = data

    cache_payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "currencies": results,
    }

    # Atomic write to avoid corrupted cache files during unexpected exits
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Use NamedTemporaryFile in the same target directory for cross-platform atomic replace
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=str(out_file.parent),
            delete=False,
            encoding="utf-8",
            suffix=".tmp",
        ) as tf:
            temp_file = tf.name
            json.dump(cache_payload, tf, indent=2)
            tf.flush()
            os.fsync(tf.fileno())

        # Atomic replace
        os.replace(temp_file, out_file)
        logger.info("Successfully refreshed news sentiment cache at %s", output_path)
    except Exception as e:
        logger.error("Failed to atomically write cache file: %s", e)
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        raise

    return cache_payload


def run_background_refresh(
    currencies: Optional[List[str]] = None,
    interval_minutes: int = 15,
    output_path: str = "data/news_sentiment_cache.json",
) -> None:
    """
    Runs periodic news sentiment refreshes at specified minute intervals.
    """
    if currencies is None:
        currencies = ["EUR", "GBP", "USD", "INR", "CNY", "JPY", "AUD"]

    logger.info(
        "Starting background news refresh loop (interval=%d min, currencies=%s)",
        interval_minutes,
        currencies,
    )
    while True:
        try:
            payload = refresh_news_cache(currencies=currencies, output_path=output_path)
            live_count = sum(
                1 for d in payload["currencies"].values() if d.get("source") == "live"
            )
            fallback_count = sum(
                1
                for d in payload["currencies"].values()
                if d.get("source") == "fallback"
            )
            logger.info(
                "Cycle complete at %s: %d live, %d fallback.",
                payload["generated_at"],
                live_count,
                fallback_count,
            )
        except Exception as e:
            logger.error("Error in background refresh cycle: %s", e)

        time.sleep(interval_minutes * 60)


# --------------------------------------------------------------------------- #
# Self-Tests (Isolated Mocks Only - No Live Network Calls)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import unittest
    from unittest.mock import MagicMock, patch

    this_mod = sys.modules[__name__]

    class TestNewsSentimentIsolated(unittest.TestCase):

        def test_01_fetch_fx_news_failure_returns_empty_and_no_raise(self):
            with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Network down")):
                result = fetch_fx_news("EUR")
                self.assertEqual(result, [])

        def test_02_extract_sentiment_empty_headlines_returns_exact_fallback(self):
            result = extract_sentiment("EUR", [])
            self.assertEqual(result, FALLBACK)

        def test_03_extract_sentiment_ollama_exception_returns_fallback(self):
            with patch.object(this_mod, "OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = Exception("Ollama connection refused")
                mock_openai.return_value = mock_client

                result = extract_sentiment("EUR", ["ECB raises rates by 50 bps"])
                self.assertEqual(result["source"], "fallback")
                self.assertEqual(result["raw"], FALLBACK["raw"])
                self.assertEqual(result["headlines"], ["ECB raises rates by 50 bps"])

        def test_04_extract_sentiment_invalid_json_returns_fallback(self):
            with patch.object(this_mod, "OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [
                    MagicMock(message=MagicMock(content="Invalid { non-json content }"))
                ]
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                result = extract_sentiment("EUR", ["ECB raises rates"])
                self.assertEqual(result["source"], "fallback")
                self.assertEqual(result["raw"], FALLBACK["raw"])
                self.assertEqual(result["headlines"], ["ECB raises rates"])

        def test_05_extract_sentiment_missing_field_returns_fallback(self):
            with patch.object(this_mod, "OpenAI") as mock_openai:
                mock_client = MagicMock()
                # Missing 'volatility_multiplier' and 'drift_bias_bps'
                mock_response = MagicMock()
                mock_response.choices = [
                    MagicMock(
                        message=MagicMock(
                            content=json.dumps(
                                {
                                    "currency": "EUR",
                                    "sentiment_score": 0.5,
                                    "confidence": 0.8,
                                }
                            )
                        )
                    )
                ]
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                result = extract_sentiment("EUR", ["ECB statement issued"])
                self.assertEqual(result["source"], "fallback")
                self.assertEqual(result["raw"], FALLBACK["raw"])
                self.assertEqual(result["headlines"], ["ECB statement issued"])

        def test_06_confidence_scaling_math(self):
            # 1. Confidence = 0.0 -> drift=0.0, multiplier=1.0
            eff_zero = compute_effective_metrics(
                raw_drift_bias_bps=-10.0,
                raw_volatility_multiplier=1.4,
                confidence=0.0,
            )
            self.assertEqual(eff_zero["drift_bias_bps"], 0.0)
            self.assertEqual(eff_zero["volatility_multiplier"], 1.0)

            # 2. Confidence = 1.0 -> exact raw values
            eff_one = compute_effective_metrics(
                raw_drift_bias_bps=-10.0,
                raw_volatility_multiplier=1.4,
                confidence=1.0,
            )
            self.assertEqual(eff_one["drift_bias_bps"], -10.0)
            self.assertEqual(eff_one["volatility_multiplier"], 1.4)

            # 3. Confidence = 0.5 -> midpoint
            eff_half = compute_effective_metrics(
                raw_drift_bias_bps=-10.0,
                raw_volatility_multiplier=1.4,
                confidence=0.5,
            )
            self.assertEqual(eff_half["drift_bias_bps"], -5.0)
            self.assertEqual(eff_half["volatility_multiplier"], 1.2)

        def test_07_refresh_news_cache_structure(self):
            mock_live_sentiment = {
                "raw": {
                    "sentiment_score": -0.6,
                    "volatility_multiplier": 1.4,
                    "drift_bias_bps": -12.0,
                    "confidence": 0.8,
                },
                "effective": {
                    "drift_bias_bps": -9.6,
                    "volatility_multiplier": 1.32,
                },
                "headline_count": 2,
                "source": "live",
            }

            temp_output = "data/test_news_cache.json"
            with patch.object(this_mod, "fetch_fx_news", return_value=["Head 1", "Head 2"]):
                with patch.object(this_mod, "extract_sentiment", return_value=mock_live_sentiment):
                    payload = refresh_news_cache(
                        currencies=["EUR", "GBP"],
                        output_path=temp_output,
                    )

            self.assertIn("generated_at", payload)
            self.assertIn("currencies", payload)
            self.assertIn("EUR", payload["currencies"])
            self.assertIn("GBP", payload["currencies"])
            self.assertEqual(payload["currencies"]["EUR"]["source"], "live")
            self.assertEqual(payload["currencies"]["EUR"]["effective"]["drift_bias_bps"], -9.6)

            # Verify file on disk
            self.assertTrue(os.path.exists(temp_output))
            with open(temp_output, "r", encoding="utf-8") as f:
                disk_data = json.load(f)
            self.assertEqual(disk_data, payload)

            # Cleanup
            if os.path.exists(temp_output):
                os.remove(temp_output)

        def test_08_atomic_write_safety(self):
            valid_file = "data/test_atomic_cache.json"
            initial_data = {"test": "valid_content"}
            Path(valid_file).parent.mkdir(parents=True, exist_ok=True)
            with open(valid_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # Simulate an error during dump inside refresh_news_cache
            with patch("json.dump", side_effect=IOError("Disk write error")):
                with self.assertRaises(IOError):
                    refresh_news_cache(currencies=["EUR"], output_path=valid_file)

            # Verify the original valid file remains untouched and uncorrupted
            with open(valid_file, "r", encoding="utf-8") as f:
                content = json.load(f)
            self.assertEqual(content, initial_data)

            # Cleanup
            if os.path.exists(valid_file):
                os.remove(valid_file)

    print("Running news_sentiment.py self-tests...")
    unittest.main()
