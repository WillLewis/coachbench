from __future__ import annotations

from pathlib import Path

from arena.storage.registry import ban_submission, connect, get_submission, list_submissions, register_submission, set_qualification_result


def test_registry_public_functions(tmp_path) -> None:
    conn = connect(":memory:")
    source = tmp_path / "agent.py"
    source.write_text("class Agent: pass\n", encoding="utf-8")
    agent_id = register_submission(conn, "owner", "agent", "v1", source, "offense", "Agent Label")
    row = get_submission(conn, agent_id)
    assert row and row["qualification_status"] == "pending"
    assert row["access_tier"] == "sandboxed_code"
    assert list_submissions(conn, "pending")[0]["agent_id"] == agent_id
    set_qualification_result(conn, agent_id, "passed", tmp_path / "report.json")
    assert get_submission(conn, agent_id)["qualification_status"] == "passed"
    ban_submission(conn, agent_id, "moderation")
    assert get_submission(conn, agent_id)["qualification_status"] == "banned"
