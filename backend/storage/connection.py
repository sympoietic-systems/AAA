import contextlib
import os
import sqlite3
import sys
import threading


class ConnectionTracker:
    def __init__(self):
        self.active_conns: dict[str, sqlite3.Connection] = {}
        self.depth = 0


_thread_conns = threading.local()


def _is_test_env(db_path: str) -> bool:
    """Return True if running in a test context or targeting a temporary test database.

    Ensures that test databases are closed immediately at depth == 0 so that
    Windows file lock teardowns (os.remove) succeed.
    """
    low = db_path.lower()
    return "test" in low or "tmp" in low or "pytest" in sys.modules


def close_thread_connections(db_path: str | None = None) -> None:
    """Explicitly close cached connections for the current thread."""
    if hasattr(_thread_conns, "cached_conns"):
        if db_path:
            conn = _thread_conns.cached_conns.pop(db_path, None)
            if conn:
                with contextlib.suppress(Exception):
                    conn.close()
        else:
            for conn in list(_thread_conns.cached_conns.values()):
                with contextlib.suppress(Exception):
                    conn.close()
            _thread_conns.cached_conns = {}


def with_connection(func):
    def wrapper(self, *args, **kwargs):
        if not hasattr(_thread_conns, "tracker") or _thread_conns.tracker is None:
            _thread_conns.tracker = ConnectionTracker()

        tracker = _thread_conns.tracker
        tracker.depth += 1
        try:
            return func(self, *args, **kwargs)
        finally:
            tracker.depth -= 1
            if tracker.depth == 0:
                # Close test database connections to release Windows file locks
                for path, conn in list(tracker.active_conns.items()):
                    if _is_test_env(path):
                        with contextlib.suppress(Exception):
                            conn.close()
                        tracker.active_conns.pop(path, None)
                        if hasattr(_thread_conns, "cached_conns"):
                            _thread_conns.cached_conns.pop(path, None)
                tracker.active_conns.clear()
                _thread_conns.tracker = None

    return wrapper


def _get_tracked_connection(db_path: str) -> sqlite3.Connection:
    if not hasattr(_thread_conns, "tracker") or _thread_conns.tracker is None:
        raise RuntimeError("Database connection requested outside of @with_connection context")

    tracker = _thread_conns.tracker
    if not hasattr(_thread_conns, "cached_conns"):
        _thread_conns.cached_conns = {}

    # Check for an existing open connection for this db_path in this thread
    conn = tracker.active_conns.get(db_path) or _thread_conns.cached_conns.get(db_path)
    if conn is not None:
        try:
            conn.execute("SELECT 1")
            tracker.active_conns[db_path] = conn
            _thread_conns.cached_conns[db_path] = conn
            return conn
        except Exception:
            with contextlib.suppress(Exception):
                conn.close()
            _thread_conns.cached_conns.pop(db_path, None)
            tracker.active_conns.pop(db_path, None)

    from .database import get_connection

    conn = get_connection(db_path)
    tracker.active_conns[db_path] = conn
    _thread_conns.cached_conns[db_path] = conn
    return conn
