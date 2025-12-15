import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.v1 import lunar as lunar_router


app = FastAPI()
app.include_router(lunar_router.router, prefix="/api/v1")


client = TestClient(app)


def test_lunar_endpoint_returns_data():
    response = client.get("/api/v1/lunar", params={"date": "2024-03-01", "tz": "UTC", "locale": "en"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "backend"
    assert "provenance" in payload
    assert "jd_ut" in payload["provenance"]


def test_lunar_endpoint_not_constant():
    one = client.get("/api/v1/lunar", params={"date": "2024-03-01", "tz": "UTC", "locale": "en"}).json()
    two = client.get("/api/v1/lunar", params={"date": "2024-03-05", "tz": "UTC", "locale": "en"}).json()

    assert one["lunar_day"] != two["lunar_day"] or one["phase_angle"] != two["phase_angle"]

