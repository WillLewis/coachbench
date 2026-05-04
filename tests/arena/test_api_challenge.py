from __future__ import annotations

import json

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app
from coachbench.contracts import HIDDEN_OBSERVATION_FIELDS, validate_challenge_report, validate_replay_contract


def test_upload_and_challenge_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "arena/storage/local").mkdir(parents=True)
    client = TestClient(app)
    source = "from agents.example_agent import ExampleCustomOffense\n"
    response = client.post("/v1/agents", json={
        "owner_id": "owner",
        "name": "local_agent",
        "version": "v1",
        "label": "Local Agent",
        "side": "offense",
        "source": source,
        "agent_path": "agents.example_agent.ExampleCustomOffense",
    })
    assert response.status_code == 200, response.text
    agent_id = response.json()["agent_id"]
    assert response.json()["status"] == "passed"
    challenge = client.post("/v1/challenges", json={"challenger_agent_id": agent_id, "opponent_kind": "static", "seeds": [42]})
    assert challenge.status_code == 200, challenge.text
    report = challenge.json()
    validate_challenge_report(report)
    assert 42 not in report["seeds"]
    assert "42" not in json.dumps(report["seeds"])
    replay = json.loads(open(report["replay_paths"][0], encoding="utf-8").read())
    validate_replay_contract(replay)
    for play in replay["plays"]:
        assert not (HIDDEN_OBSERVATION_FIELDS & set(play["offense_observed"]))
