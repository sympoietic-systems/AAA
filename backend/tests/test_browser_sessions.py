from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.api.deps import verify_password
from backend.api.routes.auth import router
from backend.core.sessions import SessionStore


def session_client(monkeypatch):
    monkeypatch.setenv("AAA_PASSWORD", "correct-password")
    app = FastAPI()
    app.include_router(router, prefix="/api", dependencies=[Depends(verify_password)])

    @app.api_route("/api/protected", methods=["GET", "POST"], dependencies=[Depends(verify_password)])
    async def protected():
        return {"ok": True}

    return TestClient(app, base_url="https://example.test")


def test_v36_session_login_logout_and_bearer_compatibility(monkeypatch):
    client = session_client(monkeypatch)
    headers = {"Origin": "https://example.test", "X-AAA-CSRF": "1", "Authorization": "Bearer wrong"}
    assert client.post("/api/auth/session", headers=headers).status_code == 401
    headers["Authorization"] = "Bearer correct-password"
    response = client.post("/api/auth/session", headers=headers)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie
    assert "correct-password" not in cookie
    assert client.get("/api/protected").status_code == 200
    assert client.get("/api/auth/verify").json()["status"] == "authenticated"
    token = client.cookies.get("aaa_session")
    assert (
        client.delete("/api/auth/session", headers={"Origin": "https://example.test", "X-AAA-CSRF": "1"}).status_code
        == 200
    )
    client.cookies.set("aaa_session", token)
    assert client.get("/api/protected").status_code == 401
    assert client.get("/api/protected", headers={"Authorization": "Bearer correct-password"}).status_code == 200


def test_v37_cookie_mutations_require_origin_and_csrf_header(monkeypatch):
    client = session_client(monkeypatch)
    headers = {"Origin": "https://example.test", "X-AAA-CSRF": "1", "Authorization": "Bearer correct-password"}
    assert client.post("/api/auth/session", headers=headers).status_code == 200
    assert client.post("/api/protected").status_code == 403
    assert client.get("/api/protected", headers={"Origin": "https://evil.test"}).status_code == 403
    assert client.post("/api/protected", headers={"Origin": "https://evil.test", "X-AAA-CSRF": "1"}).status_code == 403
    assert client.post("/api/protected", headers={"Origin": "https://example.test"}).status_code == 403
    assert (
        client.post("/api/protected", headers={"Origin": "https://example.test", "X-AAA-CSRF": "1"}).status_code == 200
    )


def test_v36_session_expiry_capacity_and_rotation(monkeypatch):
    monkeypatch.setenv("AAA_PASSWORD", "one")
    monkeypatch.setattr("backend.core.sessions.time.monotonic", lambda: 10)
    store = SessionStore(capacity=1, ttl=20)
    first = store.issue()
    second = store.issue()
    assert not store.valid(first)
    assert store.valid(second)
    monkeypatch.setattr("backend.core.sessions.time.monotonic", lambda: 30)
    assert not store.valid(second)
    third = store.issue()
    monkeypatch.setenv("AAA_PASSWORD", "two")
    assert not store.valid(third)


def test_session_ttl_env_and_default(monkeypatch):
    from backend.core.sessions import DEFAULT_SESSION_TTL, get_session_ttl

    monkeypatch.delenv("AAA_SESSION_TTL", raising=False)
    assert get_session_ttl() == 7 * 24 * 60 * 60
    assert SessionStore().ttl == DEFAULT_SESSION_TTL

    monkeypatch.setenv("AAA_SESSION_TTL", "3600")
    assert get_session_ttl() == 3600
    assert SessionStore().ttl == 3600

    monkeypatch.setenv("AAA_SESSION_TTL", "invalid")
    assert get_session_ttl() == DEFAULT_SESSION_TTL
