import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from backend.storage.connection import _get_tracked_connection, atomic_connection, commit_connection


class BaseRepository:
    def __init__(self, db_path: str | object):
        self._db_path = str(db_path)

    def _conn(self) -> sqlite3.Connection:
        return _get_tracked_connection(self._db_path)

    def _commit(self, conn: sqlite3.Connection) -> None:
        commit_connection(conn)

    @contextmanager
    def atomic(self) -> Iterator[None]:
        with atomic_connection(self._db_path):
            yield
