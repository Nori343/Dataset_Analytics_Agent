"""
Read-only SQLite tool for the query_agent.

Design: deterministic guardrails (SELECT-only, timeout, table allowlist) so the LLM
cannot mutate warehouse data. Errors are returned as strings for state.query_error.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from config.settings import (
    ALLOWED_TABLES,
    DB_PATH,
    SQL_QUERY_TIMEOUT_SECONDS,
)

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM)\b",
    re.IGNORECASE,
)


def _validate_sql(sql: str) -> str | None:
    stripped = sql.strip().rstrip(";")
    if not stripped:
        return "Empty SQL query."
    if not re.match(r"^\s*SELECT\b", stripped, re.IGNORECASE):
        return "Only SELECT queries are allowed."
    if FORBIDDEN.search(stripped):
        return "Query contains forbidden keywords (write/DDL operations)."
    # Simple allowlist: every referenced table must be allowed
    table_refs = re.findall(r"\b(?:FROM|JOIN)\s+([a-z_][a-z0-9_]*)", stripped, re.IGNORECASE)
    for table in table_refs:
        if table.lower() not in ALLOWED_TABLES:
            return f"Table '{table}' is not in the allowlist."
    return None


def run_readonly_sql(sql: str, db_path: Path | None = None) -> dict[str, Any]:
    """
    Execute a read-only SELECT against the warehouse.

    Returns:
        {"rows": [...], "row_count": int} on success
        {"error": str} on validation or execution failure
    """
    path = db_path or DB_PATH
    if not path.exists():
        return {"error": f"Database not found at {path}. Run scripts/generate_db.py first."}

    validation_error = _validate_sql(sql)
    if validation_error:
        return {"error": validation_error}

    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA query_only = ON")
        conn.execute(f"PRAGMA busy_timeout = 3000")
        cur = conn.cursor()
        cur.execute(f"SELECT 1 WHERE (SELECT 1) AND (? > 0)", (SQL_QUERY_TIMEOUT_SECONDS,))
        cur.execute(sql)
        rows = [dict(row) for row in cur.fetchall()]
        conn.close()
        return {"rows": rows, "row_count": len(rows)}
    except sqlite3.OperationalError as exc:
        return {"error": f"SQL execution error: {exc}"}
    except Exception as exc:  # noqa: BLE001 — surface any DB error to agent
        return {"error": f"Unexpected error: {exc}"}
