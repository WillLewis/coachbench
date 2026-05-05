from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.deps import ADMIN_TOKEN
from arena.api.app import app, db
from arena.storage.registry import register_submission, set_qualification_result


def test_pr1_endpoints_are_admin_gated(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "agent.py"
    source.write_text("x = 1\n", encoding="utf-8")
    conn = db()
    agent_id = register_submission(conn, "owner", "agent", "v1", source, "offense", "Agent", is_admin=True)
    set_qualification_result(conn, agent_id, "passed", None)
    client = TestClient(app)

    assert client.get(f"/v1/agents/{agent_id}").status_code == 403
    assert client.post("/v1/challenges", json={"challenger_agent_id": agent_id, "seeds": [42]}).status_code == 403
    assert client.get("/v1/challenges/missing").status_code == 403
    body = client.get(f"/v1/agents/{agent_id}", headers={"X-Admin-Token": ADMIN_TOKEN}).json()
    assert "banned_reason" not in body
    wrong = client.get(f"/v1/agents/{agent_id}", headers={"X-Admin-Token": "wrong"})
    missing = client.get(f"/v1/agents/{agent_id}")
    assert wrong.status_code == missing.status_code == 403
    assert wrong.json() == missing.json()
