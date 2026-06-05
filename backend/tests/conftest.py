import os
import shutil
from pathlib import Path
import pytest

# Force AAA_DB_PATH to use a test database file
TEST_DB_PATH = "data/aaa_test.db"
os.environ["AAA_DB_PATH"] = TEST_DB_PATH

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
