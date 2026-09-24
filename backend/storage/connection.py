import contextlib
import sqlite3
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class ConnectionTracker:
    def __init__(self):
        self.active_conns: dict[str, sqlite3.Connection] = {}
        self.depth = 0
        self.atomic_depth = 0


_thread_conns = threading.local()


def _finish_scope(tracker: ConnectionTracker) -> None:
    tracker.depth -= 1
    if tracker.depth != 0:
        return
    for path, conn in list(tracker.active_conns.items()):
        path_key = str(path)
        if _is_test_env(path_key):
            with contextlib.suppress(Exception):
                conn.close()
            tracker.active_conns.pop(path, None)
            tracker.active_conns.pop(path_key, None)
            if hasattr(_thread_conns, "cached_conns"):
                _thread_conns.cached_conns.pop(path, None)
                _thread_conns.cached_conns.pop(path_key, None)
    tracker.active_conns.clear()
    _thread_conns.tracker = None


def _is_test_env(db_path: str | object) -> bool:
    """Return True if running in a test context or targeting a temporary test database.

    Ensures that test databases are closed immediately at depth == 0 so that
    Windows file lock teardowns (os.remove) succeed.
    """
    low = str(db_path).lower()
    return "test" in low or "tmp" in low or "pytest" in sys.modules


def close_thread_connections(db_path: str | object | None = None) -> None:
    """Explicitly close cached connections for the current thread."""
    if hasattr(_thread_conns, "cached_conns"):
        if db_path is not None:
            path_key = str(db_path)
            conn = _thread_conns.cached_conns.pop(path_key, None)
            if conn:
                with contextlib.suppress(Exception):
                    conn.close()
        else:
            for conn in list(_thread_conns.cached_conns.values()):
                with contextlib.suppress(Exception):
                    conn.close()
            _thread_conns.cached_conns = {}


def with_connection(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if not hasattr(_thread_conns, "tracker") or _thread_conns.tracker is None:
            _thread_conns.tracker = ConnectionTracker()

        tracker = _thread_conns.tracker
        tracker.depth += 1
        try:
            return func(*args, **kwargs)
        finally:
            _finish_scope(tracker)

    return wrapper


def _get_tracked_connection(db_path: str | object) -> sqlite3.Connection:
    if not hasattr(_thread_conns, "tracker") or _thread_conns.tracker is None:
        raise RuntimeError("Database connection requested outside of @with_connection context")

    path_key = str(db_path)
    tracker = _thread_conns.tracker
    if not hasattr(_thread_conns, "cached_conns"):
        _thread_conns.cached_conns = {}

    # Check for an existing open connection for this db_path in this thread
    conn = tracker.active_conns.get(path_key) or _thread_conns.cached_conns.get(path_key)
    if conn is not None:
        try:
            conn.execute("SELECT 1")
            tracker.active_conns[path_key] = conn
            _thread_conns.cached_conns[path_key] = conn
            return conn
        except Exception:
            with contextlib.suppress(Exception):
                conn.close()
            _thread_conns.cached_conns.pop(path_key, None)
            tracker.active_conns.pop(path_key, None)

    from .database import get_connection

    conn = get_connection(path_key)
    tracker.active_conns[path_key] = conn
    _thread_conns.cached_conns[path_key] = conn
    return conn


def commit_connection(conn: sqlite3.Connection) -> None:
    tracker = getattr(_thread_conns, "tracker", None)
    if tracker is None or tracker.atomic_depth == 0:
        conn.commit()


@contextmanager
def atomic_connection(db_path: str | object) -> Iterator[sqlite3.Connection]:
    if not hasattr(_thread_conns, "tracker") or _thread_conns.tracker is None:
        _thread_conns.tracker = ConnectionTracker()
    tracker = _thread_conns.tracker
    tracker.depth += 1
    conn = _get_tracked_connection(db_path)
    outermost = tracker.atomic_depth == 0
    if outermost:
        conn.execute("BEGIN IMMEDIATE")
    tracker.atomic_depth += 1
    try:
        yield conn
    except BaseException:
        if outermost:
            conn.rollback()
        raise
    else:
        if outermost:
            conn.commit()
    finally:
        tracker.atomic_depth -= 1
        _finish_scope(tracker)
