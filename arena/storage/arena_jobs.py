from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def init(conn: sqlite3.Connection) -> None:
    sql = (Path(__file__).parent / "migrations" / "0004_p0_2_arena_jobs.sql").read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_progress(conn: sqlite3.Connection, job_id: str, total_runs: int) -> dict[str, Any]:
    init(conn)
    conn.execute(
        """
        INSERT OR REPLACE INTO arena_job_progress
        (job_id, completed_runs, total_runs, failed_runs, report_path, updated_at)
        VALUES (?, 0, ?, 0, NULL, ?)
        """,
        (job_id, int(total_runs), utc_now()),
    )
    conn.commit()
    row = get_progress(conn, job_id)
    if not row:
        raise RuntimeError("arena progress insert failed")
    return row


def increment_progress(conn: sqlite3.Connection, job_id: str, *, failed: bool = False) -> dict[str, Any] | None:
    init(conn)
    conn.execute(
        """
        UPDATE arena_job_progress
        SET completed_runs=completed_runs + 1,
            failed_runs=failed_runs + ?,
            updated_at=?
        WHERE job_id=?
        """,
        (1 if failed else 0, utc_now(), job_id),
    )
    conn.commit()
    return get_progress(conn, job_id)


def attach_report(conn: sqlite3.Connection, job_id: str, report_path: str) -> dict[str, Any] | None:
    init(conn)
    conn.execute(
        "UPDATE arena_job_progress SET report_path=?, updated_at=? WHERE job_id=?",
        (report_path, utc_now(), job_id),
    )
    conn.commit()
    return get_progress(conn, job_id)


def get_progress(conn: sqlite3.Connection, job_id: str) -> dict[str, Any] | None:
    init(conn)
    row = conn.execute("SELECT * FROM arena_job_progress WHERE job_id=?", (job_id,)).fetchone()
    return dict(row) if row else None
