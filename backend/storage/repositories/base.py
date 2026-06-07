import sqlite3

from backend.storage.connection import _get_tracked_connection


class BaseRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return _get_tracked_connection(self._db_path)
