from __future__ import annotations

import json
import stat

import pytest

from arena.storage.leaderboard import add_run, create_season, public_leaderboard
from arena.storage.registry import connect, get_submission, register_submission


def test_registry_stores_endpoint_hash_and_mode_0600_secret(tmp_path) -> None:
    conn = connect(":memory:")
    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")
    agent_id = register_submission(
        conn,
        "owner",
        "endpoint_agent",
        "v1",
        config,
        "offense",
        "Endpoint Agent",
        access_tier="remote_endpoint",
        endpoint_url="https://example.invalid/agent",
        api_key="secret",
        secrets_dir=tmp_path / "secrets",
    )
    row = get_submission(conn, agent_id)
    assert row["access_tier"] == "remote_endpoint"
    assert row["endpoint_url_hash"]
    secret_path = tmp_path / "secrets" / f"{agent_id}.json"
    assert "example.invalid" in json.loads(secret_path.read_text(encoding="utf-8"))["endpoint_url"]
    assert stat.S_IMODE(secret_path.stat().st_mode) == 0o600


def test_sandboxed_code_requires_admin(tmp_path) -> None:
    conn = connect(":memory:")
    source = tmp_path / "agent.py"
    source.write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(PermissionError):
        register_submission(conn, "owner", "agent", "v1", source, "offense", "Agent")
    assert register_submission(conn, "owner", "agent", "v1", source, "offense", "Agent", is_admin=True)


def test_public_leaderboard_filters_sandboxed_rows(tmp_path) -> None:
    conn = connect(":memory:")
    season = create_season(conn, "Rookie", [42], 8, "static", tmp_path / "secrets", league="rookie")
    add_run(conn, season, "public", 42, 7, "touchdown", 4, "declarative")
    add_run(conn, season, "private", 42, 3, "field_goal", 4, "sandboxed_code")
    public_ids = {row["agent_id"] for row in public_leaderboard(conn, season)["standings"]}
    assert public_ids == {"public"}
