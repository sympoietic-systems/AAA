from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.api.deps import verify_password
from backend.api.routes.preview import live_router
from backend.api.routes.preview import router as public_preview_router


def _auth_app() -> FastAPI:
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(verify_password)])
    def protected():
        return {"ok": True}

    return app


def test_v7_pytest_import_does_not_bypass_auth(monkeypatch):
    monkeypatch.setenv("AAA_PASSWORD", "correct-horse")
    client = TestClient(_auth_app())

    assert client.get("/protected").status_code == 401
    assert client.get("/protected?token=correct-horse").status_code == 401
    assert client.get("/protected", headers={"Authorization": "Bearer correct-horse"}).status_code == 200


def test_v9_public_preview_is_curated_and_live_preview_is_authenticated(monkeypatch):
    monkeypatch.setenv("AAA_PASSWORD", "preview-secret")
    app = FastAPI()
    app.include_router(public_preview_router)
    app.include_router(live_router, prefix="/api", dependencies=[Depends(verify_password)])
    client = TestClient(app)

    public_response = client.get("/api/preview/nodes")
    assert public_response.status_code == 200
    assert public_response.json()["line"]["type"] == "scar_fold"
    assert client.get("/api/preview/live").status_code == 401
    assert client.get("/api/preview/live", headers={"Authorization": "Bearer preview-secret"}).status_code == 200
