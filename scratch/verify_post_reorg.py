import json
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

print("Capturing post-reorg responses...")

with open("scratch/pre_reorg_baseline.json", "r") as f:
    baseline = json.load(f)

# Health
r_health = client.get("/health")
assert r_health.status_code == 200, f"/health failed: {r_health.status_code}"
print("[PASS] /health status 200")

# Forecast
r_forecast = client.get("/forecast?horizon=60")
assert r_forecast.status_code == 200, f"/forecast failed: {r_forecast.status_code}"
print("[PASS] /forecast?horizon=60 status 200")

# Actions
r_actions = client.get("/actions")
assert r_actions.status_code == 200, f"/actions failed: {r_actions.status_code}"
print("[PASS] /actions status 200")

# API Forecast
r_api_forecast = client.get("/api/forecast?horizon=60")
assert r_api_forecast.status_code == 200, f"/api/forecast failed: {r_api_forecast.status_code}"
data_forecast = r_api_forecast.json()
print("[PASS] /api/forecast?horizon=60 status 200")

# API Market Sentiment
r_sentiment = client.get("/api/market-sentiment")
assert r_sentiment.status_code == 200, f"/api/market-sentiment failed: {r_sentiment.status_code}"
print("[PASS] /api/market-sentiment status 200")

# Compare schemas and structural shapes with baseline
base_forecast = baseline["api_forecast"]
print("\n--- Comparative Verification ---")
print(f"Baseline forecast keys: {sorted(list(base_forecast.keys()))}")
print(f"Post-reorg forecast keys: {sorted(list(data_forecast.keys()))}")
assert sorted(list(base_forecast.keys())) == sorted(list(data_forecast.keys())), "Keys mismatch!"

print(f"Baseline expected_final_balance: {base_forecast.get('expected_final_balance')}")
print(f"Post-reorg expected_final_balance: {data_forecast.get('expected_final_balance')}")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
