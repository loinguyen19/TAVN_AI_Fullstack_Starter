"""Data access layer for validation reports.

`ReportRepository` is the seam. It is a `typing.Protocol`, so any object with
these methods satisfies it -- no base class to inherit, and tests can supply a
plain in-memory fake. Swapping SQLite for RDS (see ARCHITECTURE.md) means
adding one implementation here and changing nothing above this layer.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

DEFAULT_DB_PATH = os.environ.get("TORQUE_DB_PATH", "/var/lib/torque/reports.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  filename        TEXT    NOT NULL,
  created_at      TEXT    NOT NULL,
  document_date   TEXT,
  address_count   INTEGER NOT NULL,
  error_count     INTEGER NOT NULL,
  warning_count   INTEGER NOT NULL,
  info_count      INTEGER NOT NULL,
  payload_json    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports (created_at DESC);
"""


class ReportRepository(Protocol):
    """Persistence contract. The service depends on this, not on SQLite."""

    def initialise(self) -> None: ...

    def add(self, payload: dict[str, Any]) -> tuple[int, str]:
        """Store a report. Returns its (id, created_at)."""
        ...

    def list(self, limit: int = 50) -> list[dict[str, Any]]: ...

    def get(self, report_id: int) -> Optional[dict[str, Any]]: ...


class SqliteReportRepository:
    """SQLite implementation, insert-only.

    Each row keeps the full report payload as JSON, so history browsing and CSV
    export are a single read and a stored report stays self-describing even if
    the validators change later.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        directory = os.path.dirname(self._db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def initialise(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def add(self, payload: dict[str, Any]) -> tuple[int, str]:
        summary = payload.get("summary", {})
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        enriched = {**payload, "created_at": created_at}

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reports (filename, created_at, document_date,
                                     address_count, error_count, warning_count,
                                     info_count, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    enriched.get("filename", ""),
                    created_at,
                    enriched.get("document_date"),
                    len(enriched.get("addresses", [])),
                    summary.get("error", 0),
                    summary.get("warning", 0),
                    summary.get("info", 0),
                    "",  # placeholder; the id is only known after the insert
                ),
            )
            report_id = int(cursor.lastrowid)
            # Re-serialise with the id embedded so a replayed report is
            # identical to the response returned at creation time.
            enriched["report_id"] = report_id
            conn.execute(
                "UPDATE reports SET payload_json = ? WHERE id = ?",
                (json.dumps(enriched), report_id),
            )

        return report_id, created_at

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, filename, created_at, document_date, address_count,
                       error_count, warning_count, info_count
                FROM reports ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, report_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM reports WHERE id = ?", (report_id,)
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None
