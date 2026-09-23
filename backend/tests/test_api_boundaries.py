import ast
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.api.routes.search import router as search_router
from backend.api.schemas import ChatRequest, GenerateRequest
from backend.services.daily_summary import DailySummaryService


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"content": "x" * 50_001}, "content"),
        ({"content": "ok", "conversation_id": "../escape"}, "conversation_id"),
        ({"content": "ok", "attachments": [] * 101}, "attachments"),
        ({"content": "ok", "max_tokens": 131_073}, "max_tokens"),
    ],
)
def test_chat_request_rejects_unbounded_input(payload, field):
    if field == "attachments":
        payload["attachments"] = [{"file_name": f"{index}.txt", "file_type": "txt"} for index in range(101)]
    with pytest.raises(ValidationError) as exc_info:
        ChatRequest.model_validate(payload)
    assert field in str(exc_info.value)


def test_generate_request_rejects_invalid_identifiers_and_token_count():
    with pytest.raises(ValidationError):
        GenerateRequest(conversation_id="", user_message_id=0, max_tokens=0)


def test_search_query_bounds_are_enforced_before_route_execution():
    app = FastAPI()
    app.include_router(search_router, prefix="/api")
    response = TestClient(app).get("/api/search", params={"q": "x" * 501})
    assert response.status_code == 422


def test_daily_summary_uses_domain_validation_error():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        DailySummaryService.validate_date("../../etc/passwd")


@pytest.mark.parametrize("module_name", ["chat.py", "metrics.py", "daily_summary.py"])
def test_services_do_not_import_api_or_fastapi(module_name):
    service_path = Path(__file__).parents[1] / "services" / module_name
    tree = ast.parse(service_path.read_text(encoding="utf-8"))
    imported_roots = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "fastapi" not in imported_roots
    assert not any(module.startswith("backend.api") for module in imported_roots)
