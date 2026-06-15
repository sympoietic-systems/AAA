import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Force AAA_DB_PATH to use a test database file
TEST_DB_PATH = "data/aaa_test.db"
os.environ["AAA_DB_PATH"] = TEST_DB_PATH

# Tests need a fully migrated database
os.environ["AAA_RUN_MIGRATIONS"] = "true"


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
    # After all tests run, remove the test database files
    from backend.storage.database import get_db_path
    db_file = get_db_path(TEST_DB_PATH)
    for ext in ("", "-wal", "-shm"):
        f = Path(str(db_file) + ext)
        if f.exists():
            try:
                f.unlink()
            except Exception:
                pass
