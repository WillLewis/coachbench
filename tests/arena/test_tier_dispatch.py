from __future__ import annotations

import pytest
from pathlib import Path

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app, db
from arena.api.deps import ADMIN_TOKEN
from arena.storage.registry import register_submission, set_qualification_result
from arena.worker.main import process_one

ROOT = Path(__file__).resolve().parents[2]


def _register_config(client: TestClient, tier: str, path: str, name: str = "agent"):
    config_path = ROOT / path
    return client.post(
        "/v1/agents",
        data={"access_tier": tier, "name": name, "version": "v1", "label": name.title(), "side": "offense", "owner_id": "owner"},
        files={"tier_config": ("config.json", config_path.read_bytes(), "application/json")},
    )


def test_tier0_rookie_challenge_runs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    created = _register_config(client, "declarative", "data/agent_configs/tier0_efficiency_optimizer.json", "tier0_agent")
    assert created.status_code == 202, created.text
    challenge = client.post("/v1/challenges", json={"challenger_agent_id": created.json()["agent_id"], "league": "rookie", "seeds": [42]})
    assert challenge.status_code == 202, challenge.text
    assert process_one(tmp_path / "arena/storage/local/arena.sqlite3")
    report = client.get(f"/v1/challenges/{challenge.json()['challenge_id']}").json()
    assert report["access_tier"] == "declarative"
    assert report["league"] == "rookie"


def test_tier1_policy_league_gate(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    created = _register_config(client, "prompt_policy", "data/agent_configs/tier1_constraint_setter.json", "tier1_agent")
    assert created.status_code == 202, created.text
    assert client.post("/v1/challenges", json={"challenger_agent_id": created.json()["agent_id"], "league": "rookie", "seeds": [42]}).status_code == 422
    assert client.post("/v1/challenges", json={"challenger_agent_id": created.json()["agent_id"], "league": "policy", "seeds": [42]}).status_code == 202


def test_tier2_endpoint_league_and_public_t3_rejection(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    created = client.post(
        "/v1/agents",
        data={
            "access_tier": "remote_endpoint",
            "name": "remote_agent",
            "version": "v1",
            "label": "Remote Agent",
            "side": "offense",
            "owner_id": "owner",
            "endpoint_url": "https://example.invalid/agent",
        },
        files={"meta": ("meta.txt", b"", "text/plain")},
    )
    assert created.status_code == 202, created.text
    assert client.post("/v1/challenges", json={"challenger_agent_id": created.json()["agent_id"], "league": "endpoint", "seeds": [42]}).status_code == 202

    source = tmp_path / "agent.py"
    source.write_text("x = 1\n", encoding="utf-8")
    agent_id = register_submission(db(), "owner", "code", "v1", source, "offense", "Code", is_admin=True)
    set_qualification_result(db(), agent_id, "passed", None)
    assert client.post("/v1/challenges", json={"challenger_agent_id": agent_id, "league": "sandbox", "seeds": [42]}).status_code == 403
    assert client.post("/v1/challenges", headers={"X-Admin-Token": ADMIN_TOKEN}, json={"challenger_agent_id": agent_id, "league": "sandbox", "seeds": [42]}).status_code == 202
