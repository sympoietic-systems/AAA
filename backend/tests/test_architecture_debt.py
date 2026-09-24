import json
import subprocess
import sys
from pathlib import Path

from backend.api.schemas import ChatResponse as ApiChatResponse
from backend.api.schemas import HistoryResponse as ApiHistoryResponse
from backend.contracts import ChatResponse, HistoryResponse
from backend.errors import ServiceException
from backend.quality.architecture import debt_growth, scan_broad_catches, scan_sync_route_calls

REPO_ROOT = Path(__file__).parents[2]
DEBT_PATH = Path(__file__).with_name("architecture_debt.json")


def _debt() -> dict:
    return json.loads(DEBT_PATH.read_text(encoding="utf-8"))


def test_sync_route_debt_never_grows():
    baseline = _debt()["sync_route_calls"]
    assert debt_growth(scan_sync_route_calls(REPO_ROOT), baseline) == []


def test_broad_catch_debt_never_grows():
    baseline = _debt()["broad_catch_boundaries"]
    assert debt_growth(scan_broad_catches(REPO_ROOT), baseline) == []


def test_project_warning_debt_is_empty():
    assert _debt()["project_warning_debt"] == []


def test_compatibility_contract_exports_are_identical():
    from backend.api.exceptions import ServiceException as ApiServiceException

    assert ApiChatResponse is ChatResponse
    assert ApiHistoryResponse is HistoryResponse
    assert ApiServiceException is ServiceException


def test_v22_core_leaf_import_does_not_eagerly_load_cross_package_exports():
    code = """
import sys
import backend.core.auth

assert "backend.core.registry" not in sys.modules
from backend.core.registry import ModuleRegistry as CanonicalModuleRegistry

assert CanonicalModuleRegistry.__module__ == "backend.core.registry"
"""
    subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, check=True)
