from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.api.exceptions import raise_if_error, register_error_handlers
from backend.errors import (
    ConstraintViolation,
    GlitchError,
    ProviderGlitch,
    ResourceNotFound,
    SecurityViolation,
    ValidationGlitch,
)
from backend.quality.architecture import debt_growth, scan_broad_catches


@pytest.mark.parametrize(
    ("error", "kind", "status_code"),
    [
        (ValidationGlitch("invalid"), "validation_error", 400),
        (ConstraintViolation("conflict"), "constraint_violation", 409),
        (ResourceNotFound("missing"), "not_found", 404),
        (SecurityViolation(), "security_violation", 403),
        (ProviderGlitch("upstream"), "provider_glitch", 502),
    ],
)
def test_domain_error_taxonomy_has_fixed_translation(error: GlitchError, kind: str, status_code: int) -> None:
    assert error.kind == kind
    assert error.status_code == status_code


def test_result_translation_preserves_structured_domain_context() -> None:
    with pytest.raises(ResourceNotFound) as exc_info:
        raise_if_error(
            {
                "status": "error",
                "kind": "not_found",
                "message": "Belief is missing",
                "entity": "belief",
                "details": {"belief_id": 7},
            }
        )
    assert exc_info.value.entity == "belief"
    assert exc_info.value.details == {"belief_id": 7}


def test_api_translation_masks_ambient_and_server_error_details() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/value")
    def value_error() -> None:
        raise ValueError("invalid path C:/private/data.db")

    @app.get("/http-500")
    def http_500() -> None:
        raise HTTPException(status_code=500, detail="SQL failed at C:/private/data.db")

    client = TestClient(app, raise_server_exceptions=False)
    value_response = client.get("/value")
    server_response = client.get("/http-500")

    assert value_response.status_code == 400
    assert value_response.json()["message"] == "Invalid request value"
    assert server_response.status_code == 500
    assert server_response.json()["message"] == "Internal server error"
    assert "C:/private" not in value_response.text + server_response.text


def test_broad_catch_ratchet_tracks_callable_boundary(tmp_path: Path) -> None:
    module = tmp_path / "backend" / "services" / "worker.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        "def boundary():\n    try:\n        work()\n    except Exception:\n        raise\n",
        encoding="utf-8",
    )
    current = scan_broad_catches(tmp_path)
    assert current == {"backend/services/worker.py": {"boundary": 1}}
    assert debt_growth(current, {"backend/services/worker.py": {"other_boundary": 1}}) == [
        "backend/services/worker.py: boundary 1>0"
    ]
