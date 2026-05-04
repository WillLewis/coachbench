from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TEXT NOT NULL,
  completed_at TEXT
);
"""


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def enqueue(conn: sqlite3.Connection, kind: str, payload: dict[str, Any]) -> str:
    init(conn)
    job_id = secrets.token_hex(8)
    conn.execute(
        "INSERT INTO jobs (job_id, kind, payload_json, status, attempts, created_at) VALUES (?, ?, ?, 'pending', 0, ?)",
        (job_id, kind, json.dumps(payload), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return job_id


def get_job(conn: sqlite3.Connection, job_id: str) -> dict[str, Any] | None:
    init(conn)
    row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    return dict(row) if row else None


def claim_next(conn: sqlite3.Connection) -> dict[str, Any] | None:
    init(conn)
    row = conn.execute("SELECT * FROM jobs WHERE status='pending' ORDER BY created_at LIMIT 1").fetchone()
    if not row:
        return None
    conn.execute("UPDATE jobs SET status='running', attempts=attempts+1 WHERE job_id=?", (row["job_id"],))
    conn.commit()
    return dict(row)


def finish(conn: sqlite3.Connection, job_id: str, status: str, error: str | None = None) -> None:
    conn.execute(
        "UPDATE jobs SET status=?, last_error=?, completed_at=? WHERE job_id=?",
        (status, error, datetime.now(timezone.utc).isoformat(), job_id),
    )
    conn.commit()
