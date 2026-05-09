from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from coachbench.identities import get_identity

from arena.tiers.declarative import validate_tier_config_dict
from arena.tiers.prompt_policy import validate_tier1_config_dict


VALID_SIDE_ELIGIBILITY = {"offense", "defense", "either"}
VALID_DRAFT_TIERS = {"declarative", "prompt_policy"}


def init(conn: sqlite3.Connection) -> None:
    sql = (Path(__file__).parent / "migrations" / "0003_p0_1_backend_tables.sql").read_text(encoding="utf-8")
    conn.executescript(sql)
    if "identity_id" not in _columns(conn, "drafts"):
        sql = (Path(__file__).parent / "migrations" / "0005_p0_3_identity_columns.sql").read_text(encoding="utf-8")
        for statement in sql.split(";"):
            if "drafts" in statement:
                conn.execute(statement)
    conn.commit()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _canonical_config(config_json: str | dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if isinstance(config_json, str):
        payload = json.loads(config_json)
    else:
        payload = dict(config_json)
    if not isinstance(payload, dict):
        raise ValueError("config_json must be a JSON object")
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return text, payload


def validate_draft_config(tier: str, side_eligibility: str, config_json: str | dict[str, Any]) -> str:
    if tier not in VALID_DRAFT_TIERS:
        raise ValueError("tier must be declarative or prompt_policy")
    if side_eligibility not in VALID_SIDE_ELIGIBILITY:
        raise ValueError("side_eligibility must be offense, defense, or either")
    text, payload = _canonical_config(config_json)
    if payload.get("access_tier") != tier:
        raise ValueError("draft tier must match config access_tier")
    if side_eligibility != "either" and payload.get("side") != side_eligibility:
        raise ValueError("side_eligibility must match config side unless it is either")
    if tier == "declarative":
        validate_tier_config_dict(payload)
    else:
        validate_tier1_config_dict(payload)
    return text


def validate_identity_for_config(identity_id: str | None, config_json: str | dict[str, Any]) -> str | None:
    if not identity_id:
        return None
    _text, payload = _canonical_config(config_json)
    try:
        identity = get_identity(identity_id)
    except KeyError as exc:
        raise ValueError("unknown identity_id") from exc
    if payload.get("side") not in identity.side_eligibility:
        raise ValueError("identity is not eligible for config side")
    return identity.id


def create_draft(
    conn: sqlite3.Connection,
    *,
    name: str,
    side_eligibility: str,
    tier: str,
    config_json: str | dict[str, Any],
    identity_id: str | None = None,
) -> dict[str, Any]:
    init(conn)
    now = utc_now()
    draft_id = str(uuid.uuid4())
    config_text = validate_draft_config(tier, side_eligibility, config_json)
    identity = validate_identity_for_config(identity_id, config_text)
    conn.execute(
        """
        INSERT INTO drafts
        (id, name, version, side_eligibility, tier, config_json, identity_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (draft_id, name, 1, side_eligibility, tier, config_text, identity, now, now),
    )
    conn.commit()
    row = get_draft(conn, draft_id)
    if not row:
        raise RuntimeError("draft insert failed")
    return row


def update_draft(
    conn: sqlite3.Connection,
    draft_id: str,
    *,
    name: str | None = None,
    side_eligibility: str | None = None,
    tier: str | None = None,
    config_json: str | dict[str, Any] | None = None,
    identity_id: str | None = None,
) -> dict[str, Any] | None:
    init(conn)
    current = get_draft(conn, draft_id)
    if not current:
        return None
    next_name = name if name is not None else current["name"]
    next_side = side_eligibility if side_eligibility is not None else current["side_eligibility"]
    next_tier = tier if tier is not None else current["tier"]
    next_config = config_json if config_json is not None else current["config_json"]
    next_identity = identity_id if identity_id is not None else current.get("identity_id")
    config_text = validate_draft_config(next_tier, next_side, next_config)
    identity = validate_identity_for_config(next_identity, config_text)
    conn.execute(
        """
        UPDATE drafts
        SET name=?, version=version + 1, side_eligibility=?, tier=?, config_json=?, identity_id=?, updated_at=?
        WHERE id=?
        """,
        (next_name, next_side, next_tier, config_text, identity, utc_now(), draft_id),
    )
    conn.commit()
    return get_draft(conn, draft_id)


def bump_version(conn: sqlite3.Connection, draft_id: str) -> dict[str, Any] | None:
    init(conn)
    conn.execute(
        "UPDATE drafts SET version=version + 1, updated_at=? WHERE id=?",
        (utc_now(), draft_id),
    )
    conn.commit()
    return get_draft(conn, draft_id)


def list_drafts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    init(conn)
    rows = conn.execute("SELECT * FROM drafts ORDER BY updated_at DESC, name ASC").fetchall()
    return [dict(row) for row in rows]


def get_draft(conn: sqlite3.Connection, draft_id: str) -> dict[str, Any] | None:
    init(conn)
    return _row(conn.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone())


def delete_draft(conn: sqlite3.Connection, draft_id: str) -> bool:
    init(conn)
    cursor = conn.execute("DELETE FROM drafts WHERE id=?", (draft_id,))
    conn.commit()
    return cursor.rowcount > 0
