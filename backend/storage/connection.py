import contextlib
import sqlite3
import threading


class ConnectionTracker:
    def __init__(self):
        self.conns = []
        self.depth = 0


_thread_conns = threading.local()


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
                for conn in tracker.conns:
                    with contextlib.suppress(Exception):
                        conn.close()
                tracker.conns = []
                _thread_conns.tracker = None

    return wrapper


def _get_tracked_connection(db_path: str) -> sqlite3.Connection:
    if not hasattr(_thread_conns, "tracker") or _thread_conns.tracker is None:
        raise RuntimeError("Database connection requested outside of @with_connection context")
    from .database import get_connection

    conn = get_connection(db_path)
    _thread_conns.tracker.conns.append(conn)
    return conn
