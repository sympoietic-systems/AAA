import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.exceptions import ServiceException, register_error_handlers
from backend.api.routes.errors import router as errors_router
from backend.core.logging_config import (
    SecretMaskingFilter,
    setup_logging,
    tail_log_file,
)


def test_secret_masking_filter():
    """Verify SecretMaskingFilter scrubs tokens, API keys, and passwords."""
    filter_ = SecretMaskingFilter()

    # 1. Bearer token
    record1 = logging.LogRecord("test", logging.INFO, "test.py", 10, "Auth Bearer eyJhbGciOiJIUzI1NiJ9", (), None)
    filter_.filter(record1)
    assert "Bearer [REDACTED]" in record1.msg
    assert "eyJhbGciOi" not in record1.msg

    # 2. OpenAI-style sk- key
    mock_sk = "sk-" + "test1234567890abcdefghijklmnopqrstuvwxyz"
    record2 = logging.LogRecord("test", logging.ERROR, "test.py", 12, f"Key {mock_sk}", (), None)
    filter_.filter(record2)
    assert "sk-[REDACTED]" in record2.msg
    assert "test1234567890abcdef" not in record2.msg

    # 3. Google AIza key
    mock_aiza = "AIza" + "SyD_fake123456789012345678901234567890"
    record3 = logging.LogRecord("test", logging.WARNING, "test.py", 14, f"Found {mock_aiza} in config", (), None)
    filter_.filter(record3)
    assert "AIza[REDACTED]" in record3.msg

    # 4. OpenRouter key (constructed dynamically so static scanners don't false-positive)
    mock_openrouter = "sk" + "-or-v1-" + ("ab12" * 16)
    record4 = logging.LogRecord(
        "test",
        logging.ERROR,
        "test.py",
        16,
        f"Failed key {mock_openrouter}",
        (),
        None,
    )
    filter_.filter(record4)
    assert "sk-or-v1-[REDACTED]" in record4.msg

    # 5. Password parameter in args
    record5 = logging.LogRecord(
        "test", logging.INFO, "test.py", 18, "Credentials: %s", ("password=SecretPassword123",), None
    )
    filter_.filter(record5)
    assert "password=[REDACTED]" in record5.args[0]
    assert "SecretPassword123" not in record5.args[0]


def test_setup_logging_files_and_levels(tmp_path: Path):
    """Verify error.log and server.log receive the correct log levels and masked secrets."""
    log_dir = tmp_path / "logs"
    config = {
        "logging": {
            "enabled": True,
            "dir": str(log_dir),
            "level": "INFO",
            "error_level": "WARNING",
            "max_bytes": 1024 * 1024,
            "backup_count": 3,
        }
    }

    setup_logging(config)

    test_logger = logging.getLogger("test_subsystem")
    test_logger.info("Routine operation heartbeat: Bearer my_secret_token_123")
    test_logger.warning("Elevated warning: sk-abcdefghijklmnopqrstuvwxyz123456 rate limited")
    test_logger.error("Critical failure: database connection dropped")

    error_file = log_dir / "error.log"
    server_file = log_dir / "server.log"

    assert error_file.exists()
    assert server_file.exists()

    error_content = error_file.read_text(encoding="utf-8")
    server_content = server_file.read_text(encoding="utf-8")

    # error.log should NOT have INFO logs
    assert "Routine operation heartbeat" not in error_content
    # error.log SHOULD have WARNING and ERROR logs
    assert "Elevated warning" in error_content
    assert "Critical failure" in error_content

    # server.log should have all three
    assert "Routine operation heartbeat" in server_content
    assert "Elevated warning" in server_content
    assert "Critical failure" in server_content

    # Secrets must be redacted on disk in both files
    assert "my_secret_token_123" not in server_content
    assert "Bearer [REDACTED]" in server_content
    assert "sk-[REDACTED]" in error_content
    assert "abcdefghijklmnopqrstuvwxyz123456" not in error_content


def test_file_rotation(tmp_path: Path):
    """Verify log rotation triggers and preserves backupCount archives."""
    log_dir = tmp_path / "rotation_logs"
    config = {
        "logging": {
            "enabled": True,
            "dir": str(log_dir),
            "level": "INFO",
            "error_level": "WARNING",
            "max_bytes": 500,  # Tiny threshold to trigger immediate rotation
            "backup_count": 2,
        }
    }

    setup_logging(config)
    test_logger = logging.getLogger("rotation_tester")

    # Write enough warnings to exceed 500 bytes multiple times
    for i in range(40):
        test_logger.warning("Rotation warning event payload line number %03d with extra padding", i)

    error_file = log_dir / "error.log"
    rot1_file = log_dir / "error.log.1"

    assert error_file.exists()
    assert rot1_file.exists()

    # backupCount was 2, so .3 should not exist
    rot3_file = log_dir / "error.log.3"
    assert not rot3_file.exists()


def test_tail_log_file(tmp_path: Path):
    """Verify reverse block tailing accurately reads the last N lines."""
    test_file = tmp_path / "sample.log"
    lines = [f"Log line {i:03d}" for i in range(100)]
    test_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Tail last 10 lines
    last_10 = tail_log_file(test_file, max_lines=10)
    assert len(last_10) == 10
    assert last_10[0] == "Log line 090"
    assert last_10[-1] == "Log line 099"

    # Tail more lines than file has
    all_lines = tail_log_file(test_file, max_lines=200)
    assert len(all_lines) == 100
    assert all_lines[0] == "Log line 000"

    # Non-existent file
    empty = tail_log_file(tmp_path / "missing.log", max_lines=10)
    assert empty == []


def test_global_exception_handler_and_glitch(tmp_path: Path):
    """Verify unhandled exceptions are logged with traceback and return structured Glitch payload."""
    log_dir = tmp_path / "glitch_logs"
    setup_logging({"logging": {"enabled": True, "dir": str(log_dir)}})

    app = FastAPI()
    register_error_handlers(app)

    @app.get("/trigger-crash")
    def trigger_crash():
        raise RuntimeError("Fatal internal kernel collapse")

    @app.get("/trigger-service-error")
    def trigger_service_error():
        raise ServiceException("Entity not accessible", status_code=404)

    client = TestClient(app, raise_server_exceptions=False)

    # 1. Unhandled 500 crash
    res_crash = client.get("/trigger-crash")
    assert res_crash.status_code == 500
    data_crash = res_crash.json()
    assert data_crash["status"] == "error"
    assert data_crash["kind"] == "internal_error"
    # Ensure internal traceback is not exposed to the client
    assert "Fatal internal kernel collapse" not in data_crash["message"]

    # Verify traceback was written to error.log
    error_log = log_dir / "error.log"
    assert error_log.exists()
    error_content = error_log.read_text(encoding="utf-8")
    assert "Unhandled server crash" in error_content
    assert "RuntimeError: Fatal internal kernel collapse" in error_content

    # 2. ServiceException
    res_service = client.get("/trigger-service-error")
    assert res_service.status_code == 404
    data_service = res_service.json()
    assert data_service["status"] == "error"
    assert data_service["kind"] == "service_error"
    assert data_service["message"] == "Entity not accessible"


def test_logs_tail_endpoint(tmp_path: Path):
    """Verify /api/errors/logs endpoint retrieves sanitized tail lines with parameter validation."""
    log_dir = tmp_path / "api_logs"
    setup_logging({"logging": {"enabled": True, "dir": str(log_dir)}})

    app = FastAPI()
    app.state.config = {"logging": {"dir": str(log_dir)}}
    app.include_router(errors_router, prefix="/api")

    # Populate error.log
    err_logger = logging.getLogger("api_test")
    err_logger.warning("Warn 1: Bearer token_abc")
    mock_sk_tail = "sk-" + "testkey1234567890abcdef"
    err_logger.error(f"Error 2: {mock_sk_tail}")

    client = TestClient(app)

    # Query error logs
    res = client.get("/api/errors/logs?type=error&lines=10")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["log_type"] == "error"
    assert data["count"] >= 2
    # Ensure secrets scrubbed in response
    combined = " ".join(data["lines"])
    assert "Bearer [REDACTED]" in combined
    assert "token_abc" not in combined
    assert "sk-[REDACTED]" in combined

    # Query server logs
    res_server = client.get("/api/errors/logs?type=server&lines=5")
    assert res_server.status_code == 200
    assert res_server.json()["log_type"] == "server"

    # Clamping validation: lines > 500 should fail validation
    res_overflow = client.get("/api/errors/logs?type=error&lines=9999")
    assert res_overflow.status_code == 422
