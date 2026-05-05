from __future__ import annotations

import sqlite3

import pytest

from arena.storage.registry import connect, get_submission, register_submission


def test_fresh_registry_has_tier_columns_and_check(tmp_path) -> None:
    conn = connect(":memory:")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(agent_submissions)").fetchall()}
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='agent_submissions'").fetchone()[0]
    assert {"access_tier", "tier_config_path", "endpoint_url_hash"} <= columns
    assert "declarative" in sql and "sandboxed_code" in sql

    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(sqlite3.IntegrityError):
        register_submission(conn, "o", "bad", "v1", source, "offense", "Bad", access_tier="bad", is_admin=True)


def test_non_admin_may_register_public_tiers_but_not_sandboxed_code(tmp_path) -> None:
    conn = connect(":memory:")
    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    agent_id = register_submission(conn, "o", "agent", "v1", source, "offense", "Agent", access_tier="declarative")
    assert get_submission(conn, agent_id)["access_tier"] == "declarative"
    with pytest.raises(PermissionError):
        register_submission(conn, "o", "agent2", "v1", source, "offense", "Agent", access_tier="sandboxed_code")


def test_admin_forward_compat_tier_insert_succeeds(tmp_path) -> None:
    conn = connect(":memory:")
    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    agent_id = register_submission(conn, "o", "agent", "v1", source, "offense", "Agent", access_tier="declarative", is_admin=True)
    assert get_submission(conn, agent_id)["access_tier"] == "declarative"


def test_legacy_registry_migration_is_idempotent(tmp_path) -> None:
    db = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE agent_submissions (
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
          UNIQUE(owner_id, name, version)
        );
        INSERT INTO agent_submissions VALUES ('a','o','n','v','h','s.py','offense','now','pending',NULL,'Label',NULL);
        """
    )
    conn.commit()
    conn.close()
    first = connect(db)
    second = connect(db)
    assert get_submission(second, "a")["access_tier"] == "sandboxed_code"
