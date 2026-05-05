from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_submissions (
  agent_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  source_path TEXT NOT NULL,
  side TEXT NOT NULL,
  submitted_at TEXT NOT NULL,
  qualification_status TEXT NOT NULL,
  qualification_report_path TEXT,
  label TEXT NOT NULL,
  banned_reason TEXT,
  access_tier TEXT NOT NULL DEFAULT 'sandboxed_code',
  tier_config_path TEXT,
  endpoint_url_hash TEXT,
  UNIQUE(owner_id, name, version),
  CHECK(access_tier IN ('declarative', 'prompt_policy',
                        'remote_endpoint',
                        'sandboxed_code'))
);
CREATE INDEX IF NOT EXISTS idx_status ON agent_submissions(qualification_status);
"""


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _columns(conn: sqlite3.Connection) -> set[str]:
    return {row[1] for row in conn.execute("PRAGMA table_info(agent_submissions)").fetchall()}


def _migrate(conn: sqlite3.Connection) -> None:
    if "access_tier" in _columns(conn):
        return
    sql = (Path(__file__).parent / "migrations" / "0001_pr1_tier_columns.sql").read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def register_submission(
    conn: sqlite3.Connection,
    owner_id: str,
    name: str,
    version: str,
    source_path: Path,
    side: str,
    label: str,
    access_tier: str = "sandboxed_code",
    is_admin: bool = False,
    tier_config_path: str | None = None,
    endpoint_url_hash: str | None = None,
) -> str:
    if access_tier != "sandboxed_code" and not is_admin:
        raise PermissionError("Only admin callers may register non-sandbox tiers")
    source = source_path.read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    agent_id = hashlib.sha256(f"{owner_id}:{name}:{version}:{source_hash}".encode()).hexdigest()[:16]
    conn.execute(
        """
        INSERT INTO agent_submissions
        (agent_id, owner_id, name, version, source_hash, source_path, side, submitted_at,
         qualification_status, label, access_tier, tier_config_path, endpoint_url_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agent_id,
            owner_id,
            name,
            version,
            source_hash,
            str(source_path),
            side,
            datetime.now(timezone.utc).isoformat(),
            "pending",
            label,
            access_tier,
            tier_config_path,
            endpoint_url_hash,
        ),
    )
    conn.commit()
    return agent_id


def set_qualification_result(conn: sqlite3.Connection, agent_id: str, status: str, report_path: Path | str | None, banned_reason: str | None = None) -> None:
    conn.execute(
        "UPDATE agent_submissions SET qualification_status=?, qualification_report_path=?, banned_reason=? WHERE agent_id=?",
        (status, str(report_path) if report_path else None, banned_reason, agent_id),
    )
    conn.commit()


def get_submission(conn: sqlite3.Connection, agent_id: str) -> dict[str, Any] | None:
    return _row(conn.execute("SELECT * FROM agent_submissions WHERE agent_id=?", (agent_id,)).fetchone())


def list_submissions(conn: sqlite3.Connection, status: str | None = None) -> list[dict[str, Any]]:
    if status:
        rows = conn.execute("SELECT * FROM agent_submissions WHERE qualification_status=? ORDER BY submitted_at", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM agent_submissions ORDER BY submitted_at").fetchall()
    return [dict(row) for row in rows]


def ban_submission(conn: sqlite3.Connection, agent_id: str, reason: str) -> None:
    set_qualification_result(conn, agent_id, "banned", None, reason)
