"""Bounded read-only inspection of application database tables."""

from __future__ import annotations

import re
from typing import Any

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository

_FILTER_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "contains", "is_null", "not_null"}
_SENSITIVE_COLUMN = re.compile(
    r"password|secret|token|api[_-]?key|credential|cookie|authorization|private[_-]?key", re.I
)
_MAX_CELL_TEXT = 4096


class DatabaseInspectionRepository(BaseRepository):
    """Read table metadata and small row windows without exposing SQL execution."""

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    @with_connection
    def list_tables(self) -> list[dict[str, Any]]:
        conn = self._conn()
        table_names = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        tables: list[dict[str, Any]] = []
        for row in table_names:
            table_name = str(row["name"])
            quoted_name = self._quote_identifier(table_name)
            columns = conn.execute(f"PRAGMA table_info({quoted_name})").fetchall()
            tables.append({"table_name": table_name, "columns": [str(column["name"]) for column in columns]})
        return tables

    @with_connection
    def read_rows(
        self,
        *,
        table_name: str,
        columns: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        order_by: str | None = None,
        descending: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        conn = self._conn()
        table_row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)
        ).fetchone()
        if table_row is None:
            raise LookupError("Database table not found")

        table_columns = [
            str(row["name"]) for row in conn.execute(f"PRAGMA table_info({self._quote_identifier(table_name)})")
        ]
        if not table_columns:
            raise LookupError("Database table has no inspectable columns")
        selected_columns = columns or table_columns
        if len(selected_columns) > 30 or any(column not in table_columns for column in selected_columns):
            raise ValueError("Select up to 30 exact column names returned by the schema tool")
        if order_by is not None and order_by not in table_columns:
            raise ValueError("order_by must be an exact column name returned by the schema tool")

        where_clauses: list[str] = []
        values: list[object] = []
        for item in filters or []:
            column = item.get("column")
            operator = item.get("operator")
            value = item.get("value")
            if column not in table_columns or operator not in _FILTER_OPERATORS:
                raise ValueError("Each filter must use an exact column name and supported operator")
            quoted_column = self._quote_identifier(column)
            if operator == "is_null":
                where_clauses.append(f"{quoted_column} IS NULL")
            elif operator == "not_null":
                where_clauses.append(f"{quoted_column} IS NOT NULL")
            elif operator == "contains":
                if not isinstance(value, str):
                    raise ValueError("contains filters require a text value")
                escaped_value = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                where_clauses.append(f"{quoted_column} LIKE ? ESCAPE '\\'")
                values.append(f"%{escaped_value}%")
            else:
                if value is None:
                    raise ValueError("Comparison filters require a non-null value")
                sql_operator = {"eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}[operator]
                where_clauses.append(f"{quoted_column} {sql_operator} ?")
                values.append(value)

        query = "SELECT " + ", ".join(self._quote_identifier(column) for column in selected_columns)
        query += f" FROM {self._quote_identifier(table_name)}"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        if order_by:
            query += f" ORDER BY {self._quote_identifier(order_by)} {'DESC' if descending else 'ASC'}"
        query += " LIMIT ? OFFSET ?"
        values.extend((limit + 1, offset))
        fetched = conn.execute(query, values).fetchall()
        truncated = len(fetched) > limit
        rows = fetched[:limit]

        sanitized_rows: list[dict[str, Any]] = []
        for row in rows:
            safe_row: dict[str, Any] = {}
            for column in selected_columns:
                value = row[column]
                if _SENSITIVE_COLUMN.search(column):
                    safe_row[column] = "[REDACTED]"
                elif isinstance(value, bytes):
                    safe_row[column] = {"blob_bytes": len(value)}
                elif isinstance(value, str) and len(value) > _MAX_CELL_TEXT:
                    safe_row[column] = value[:_MAX_CELL_TEXT] + "…[truncated]"
                else:
                    safe_row[column] = value
            sanitized_rows.append(safe_row)

        return {
            "table_name": table_name,
            "columns": selected_columns,
            "rows": sanitized_rows,
            "limit": limit,
            "offset": offset,
            "has_more": truncated,
        }
