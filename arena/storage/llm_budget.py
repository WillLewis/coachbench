from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def init(conn: sqlite3.Connection) -> None:
    sql = (Path(__file__).parent / "migrations" / "0003_p0_1_backend_tables.sql").read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def since_iso(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=int(seconds))).isoformat()


def count_session_calls(conn: sqlite3.Connection, session_id: str) -> int:
    init(conn)
    return int(conn.execute("SELECT COUNT(*) FROM llm_calls WHERE session_id=?", (session_id,)).fetchone()[0])


def count_ip_window_calls(conn: sqlite3.Connection, ip: str, window_seconds: int) -> int:
    init(conn)
    return int(
        conn.execute(
            "SELECT COUNT(*) FROM llm_calls WHERE ip=? AND ts>=?",
            (ip, since_iso(window_seconds)),
        ).fetchone()[0]
    )


def count_concurrent_sessions(conn: sqlite3.Connection) -> int:
    init(conn)
    return int(conn.execute("SELECT COUNT(*) FROM llm_concurrency").fetchone()[0])


def calls_since(conn: sqlite3.Connection, seconds: int) -> int:
    init(conn)
    return int(conn.execute("SELECT COUNT(*) FROM llm_calls WHERE ts>=?", (since_iso(seconds),)).fetchone()[0])


def total_cost_usd(conn: sqlite3.Connection) -> float:
    init(conn)
    value = conn.execute("SELECT COALESCE(SUM(cost_usd_est), 0.0) FROM llm_calls").fetchone()[0]
    return float(value or 0.0)


def begin_concurrency(conn: sqlite3.Connection, session_id: str) -> None:
    init(conn)
    conn.execute(
        "INSERT OR REPLACE INTO llm_concurrency (session_id, started_at) VALUES (?, ?)",
        (session_id, utc_now()),
    )
    conn.commit()


def end_concurrency(conn: sqlite3.Connection, session_id: str) -> None:
    init(conn)
    conn.execute("DELETE FROM llm_concurrency WHERE session_id=?", (session_id,))
    conn.commit()


def record_call(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    ip: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd_est: float = 0.0,
) -> dict[str, Any]:
    init(conn)
    call_id = secrets.token_hex(8)
    conn.execute(
        """
        INSERT INTO llm_calls
        (id, session_id, ip, ts, tokens_in, tokens_out, cost_usd_est)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (call_id, session_id, ip, utc_now(), int(tokens_in), int(tokens_out), float(cost_usd_est)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM llm_calls WHERE id=?", (call_id,)).fetchone()
    return dict(row)
