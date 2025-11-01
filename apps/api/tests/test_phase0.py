from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200

def test_send_otp_endpoint_exists():
    r = client.post("/v1/auth/otp:send", json={"email":"user@example.com"})
    assert r.status_code == 200
    assert r.json().get("ok") is True
