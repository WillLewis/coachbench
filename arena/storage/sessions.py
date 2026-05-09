from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_SESSION_STATUSES = {"completed", "running", "failed"}


def init(conn: sqlite3.Connection) -> None:
    sql = (Path(__file__).parent / "migrations" / "0003_p0_1_backend_tables.sql").read_text(encoding="utf-8")
    conn.executescript(sql)
    if "offense_label" not in _columns(conn, "sessions"):
        sql = (Path(__file__).parent / "migrations" / "0005_p0_3_identity_columns.sql").read_text(encoding="utf-8")
        for statement in sql.split(";"):
            if "sessions" in statement:
                conn.execute(statement)
    conn.commit()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def create_session(
    conn: sqlite3.Connection,
    *,
    offense_draft_id: str,
    defense_draft_id: str,
    seed: int,
    status: str = "running",
    opponent_label: str | None = None,
    seed_pack: str | None = None,
    report_path: str | None = None,
    session_id: str | None = None,
    offense_label: str | None = None,
    defense_label: str | None = None,
    offense_technical_label: str | None = None,
    defense_technical_label: str | None = None,
) -> dict[str, Any]:
    init(conn)
    if status not in VALID_SESSION_STATUSES:
        raise ValueError("invalid session status")
    run_id = session_id or str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO sessions
        (id, created_at, offense_draft_id, defense_draft_id, opponent_label, seed,
         seed_pack, report_path, replay_paths_json, status, offense_label, defense_label,
         offense_technical_label, defense_technical_label)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            utc_now(),
            offense_draft_id,
            defense_draft_id,
            opponent_label,
            int(seed),
            seed_pack,
            report_path,
            "[]",
            status,
            offense_label,
            defense_label,
            offense_technical_label,
            defense_technical_label,
        ),
    )
    conn.commit()
    row = get_session(conn, run_id)
    if not row:
        raise RuntimeError("session insert failed")
    return row


def get_session(conn: sqlite3.Connection, session_id: str) -> dict[str, Any] | None:
    init(conn)
    return _row(conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone())


def update_session_status(conn: sqlite3.Connection, session_id: str, status: str, report_path: str | None = None) -> dict[str, Any] | None:
    init(conn)
    if status not in VALID_SESSION_STATUSES:
        raise ValueError("invalid session status")
    conn.execute(
        "UPDATE sessions SET status=?, report_path=COALESCE(?, report_path) WHERE id=?",
        (status, report_path, session_id),
    )
    conn.commit()
    return get_session(conn, session_id)


def attach_replays(conn: sqlite3.Connection, session_id: str, replay_paths: list[str]) -> dict[str, Any] | None:
    init(conn)
    conn.execute(
        "UPDATE sessions SET replay_paths_json=? WHERE id=?",
        (json.dumps(list(replay_paths), sort_keys=True), session_id),
    )
    conn.commit()
    return get_session(conn, session_id)


def list_sessions(conn: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    init(conn)
    rows = conn.execute(
        "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?",
        (int(limit),),
    ).fetchall()
    return [dict(row) for row in rows]
