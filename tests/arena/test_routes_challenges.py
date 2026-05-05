from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.deps import ADMIN_TOKEN
from arena.api.app import app, db
from arena.storage.registry import register_submission, set_qualification_result


def _agent(tmp_path, status: str = "passed") -> str:
    source = tmp_path / "agent.py"
    source.write_text("x = 1\n", encoding="utf-8")
    conn = db()
    agent_id = register_submission(conn, "owner", "agent", "v1", source, "offense", "Agent", is_admin=True)
    set_qualification_result(conn, agent_id, status, None)
    return agent_id


def test_challenge_admin_happy_path(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    agent_id = _agent(tmp_path)
    response = TestClient(app).post(
        "/v1/challenges",
        json={"challenger_agent_id": agent_id, "opponent_kind": "static", "seeds": [42]},
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    assert response.status_code == 202, response.text
    assert response.json()["job_id"]


def test_challenge_requires_admin_token(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    agent_id = _agent(tmp_path)
    response = TestClient(app).post("/v1/challenges", json={"challenger_agent_id": agent_id, "seeds": [42]})
    assert response.status_code == 403


def test_challenge_rejects_unqualified_agent(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    agent_id = _agent(tmp_path, "pending")
    response = TestClient(app).post(
        "/v1/challenges",
        json={"challenger_agent_id": agent_id, "seeds": [42]},
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    assert response.status_code == 422
