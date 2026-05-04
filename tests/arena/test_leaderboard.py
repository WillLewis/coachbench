from __future__ import annotations

from arena.storage.leaderboard import add_run, create_season, snapshot
from arena.storage.registry import connect
from coachbench.contracts import validate_leaderboard_snapshot


def test_leaderboard_snapshot_hides_raw_seeds_and_is_deterministic(tmp_path) -> None:
    conn = connect(":memory:")
    season = create_season(conn, "Local Season", [42, 99], 8, "static", tmp_path / "secrets")
    add_run(conn, season, "agent_a", 42, 7, "touchdown", 3)
    add_run(conn, season, "agent_a", 99, 3, "field_goal", 8)
    add_run(conn, season, "agent_b", 42, 0, "stopped", 8)
    add_run(conn, season, "agent_b", 99, 3, "field_goal", 8)
    first = snapshot(conn, season, {"agent_a": "Agent A", "agent_b": "Agent B"})
    second = snapshot(conn, season, {"agent_a": "Agent A", "agent_b": "Agent B"})
    validate_leaderboard_snapshot(first)
    assert first == second
    assert first["standings"][0]["agent_id"] == "agent_a"
    assert "42" not in str(first)
