from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS leaderboard_seasons (
  season_id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  seed_set_hash TEXT NOT NULL,
  max_plays INTEGER NOT NULL,
  opponent_kind TEXT NOT NULL,
  league TEXT NOT NULL DEFAULT 'sandbox',
  created_at TEXT NOT NULL,
  closed_at TEXT,
  CHECK(league IN ('rookie','policy','endpoint','sandbox','research'))
);
CREATE TABLE IF NOT EXISTS leaderboard_runs (
  run_id TEXT PRIMARY KEY,
  season_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  seed_hash TEXT NOT NULL,
  points INTEGER NOT NULL,
  result TEXT NOT NULL,
  plays INTEGER NOT NULL,
  access_tier TEXT NOT NULL DEFAULT 'sandboxed_code',
  created_at TEXT NOT NULL,
  UNIQUE(season_id, agent_id, seed_hash)
);
"""


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate(conn: sqlite3.Connection) -> None:
    if "league" in _columns(conn, "leaderboard_seasons") and "access_tier" in _columns(conn, "leaderboard_runs"):
        return
    sql = (Path(__file__).parent / "migrations" / "0002_pr1_leaderboard_columns.sql").read_text(encoding="utf-8")
    conn.executescript(sql)


def seed_hash(seed: int) -> str:
    return hashlib.sha256(str(seed).encode()).hexdigest()[:12]


def seed_set_hash(seeds: list[int]) -> str:
    return hashlib.sha256(json.dumps(sorted(seeds)).encode()).hexdigest()


def create_season(conn: sqlite3.Connection, label: str, seeds: list[int], max_plays: int, opponent_kind: str, secrets_dir: Path, league: str = "sandbox") -> str:
    init(conn)
    season_id = secrets.token_hex(8)
    conn.execute(
        "INSERT INTO leaderboard_seasons VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
        (season_id, label, seed_set_hash(seeds), max_plays, opponent_kind, league, datetime.now(timezone.utc).isoformat()),
    )
    secrets_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    secret_path = secrets_dir / f"{season_id}.json"
    secret_path.write_text(json.dumps({"seeds": seeds}) + "\n", encoding="utf-8")
    secret_path.chmod(0o600)
    conn.commit()
    return season_id


def add_run(conn: sqlite3.Connection, season_id: str, agent_id: str, seed: int, points: int, result: str, plays: int, access_tier: str = "sandboxed_code") -> None:
    init(conn)
    conn.execute(
        "INSERT OR REPLACE INTO leaderboard_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (secrets.token_hex(8), season_id, agent_id, seed_hash(seed), points, result, plays, access_tier, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def snapshot(conn: sqlite3.Connection, season_id: str, labels: dict[str, str] | None = None, include_sandboxed: bool = True) -> dict[str, Any]:
    init(conn)
    season = conn.execute("SELECT * FROM leaderboard_seasons WHERE season_id=?", (season_id,)).fetchone()
    if include_sandboxed:
        rows = conn.execute("SELECT * FROM leaderboard_runs WHERE season_id=?", (season_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM leaderboard_runs WHERE season_id=? AND access_tier != 'sandboxed_code'", (season_id,)).fetchall()
    grouped: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["agent_id"], []).append(row)
    standings = []
    for agent_id, runs in grouped.items():
        points = [row["points"] for row in runs]
        touchdowns = [1.0 if row["result"] == "touchdown" else 0.0 for row in runs]
        standings.append({
            "agent_id": agent_id,
            "label": (labels or {}).get(agent_id, agent_id),
            "games_played": len(runs),
            "mean_points_per_drive": round(sum(points) / len(points), 4) if points else 0.0,
            "touchdown_rate": round(sum(touchdowns) / len(touchdowns), 4) if touchdowns else 0.0,
        })
    standings.sort(key=lambda row: (-row["mean_points_per_drive"], row["agent_id"]))
    return {"season_id": season_id, "seed_set_hash": season["seed_set_hash"] if season else "", "standings": standings}
