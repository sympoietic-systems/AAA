import contextlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Force AAA_DB_PATH to use a test database file
TEST_DB_PATH = "data/aaa_test.db"
os.environ["AAA_DB_PATH"] = TEST_DB_PATH

# Tests need a fully migrated database
os.environ["AAA_RUN_MIGRATIONS"] = "true"


@pytest.fixture(autouse=True)
def isolate_auth_environment(monkeypatch):
    """Keep ordinary tests independent of developer credentials and live providers."""
    monkeypatch.setenv("AAA_PASSWORD", "")
    for key in (
        "AAA_LLM_API_KEY",
        "AAA_BACKGROUND_API_KEY",
        "AAA_VISION_API_KEY",
        "AAA_STRUCTURAL_API_KEY",
        "AAA_TYPESAFE_API_KEY",
        "TYPESAFE_API_KEY",
        "AAA_GOOGLE_API_KEY",
        "AAA_DEEPSEEK_API_KEY",
        "AAA_NVIDIA_API_KEY",
    ):
        monkeypatch.setenv(key, "")


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Shared FastAPI TestClient for route-level integration tests.

    Replaces the 18 inline `TestClient(app)` calls across 8 test files.
    Uses session scope to avoid re-creating the app for every test.
    """
    from backend.main import app

    app.state.config = {}  # Prevent lifespan from running in tests
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    # Force garbage collection to close unreferenced SQLite connections on Windows
    import gc

    gc.collect()

    # After all tests run, remove test database files and any ephemeral test db leftovers
    from backend.storage.database import get_db_path

    db_file = get_db_path(TEST_DB_PATH)
    data_dir = db_file.parent

    # Clean specific default test db
    for ext in ("", "-wal", "-shm"):
        f = Path(str(db_file) + ext)
        if f.exists():
            with contextlib.suppress(Exception):
                f.unlink()

    # Clean any other ephemeral test database files (*test*.db*)
    if data_dir.exists():
        for test_db in data_dir.glob("*test*.db*"):
            with contextlib.suppress(Exception):
                test_db.unlink()
