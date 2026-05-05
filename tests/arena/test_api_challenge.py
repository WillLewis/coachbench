from __future__ import annotations

import json

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app
from arena.api.deps import ADMIN_TOKEN
from arena.worker.main import process_one
from coachbench.contracts import HIDDEN_OBSERVATION_FIELDS, validate_challenge_report, validate_replay_contract


def test_upload_and_challenge_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "arena/storage/local").mkdir(parents=True)
    client = TestClient(app)
    source = "from agents.example_agent import ExampleCustomOffense\n"
    response = client.post(
        "/v1/agents",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        data={"owner_id": "owner", "name": "local_agent", "version": "v1", "label": "Local Agent", "side": "offense"},
        files={"file": ("agent.py", source, "text/x-python")},
    )
    assert response.status_code == 202, response.text
    agent_id = response.json()["agent_id"]
    assert process_one(tmp_path / "arena/storage/local/arena.sqlite3")
    challenge = client.post(
        "/v1/challenges",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        json={"challenger_agent_id": agent_id, "opponent_kind": "static", "seeds": [42]},
    )
    assert challenge.status_code == 202, challenge.text
    assert process_one(tmp_path / "arena/storage/local/arena.sqlite3")
    report_response = client.get(f"/v1/challenges/{challenge.json()['challenge_id']}", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()
    validate_challenge_report(report)
    assert 42 not in report["seeds"]
    assert "42" not in json.dumps(report["seeds"])
    replay = json.loads(open(report["replay_paths"][0], encoding="utf-8").read())
    validate_replay_contract(replay)
    for play in replay["plays"]:
        assert not (HIDDEN_OBSERVATION_FIELDS & set(play["offense_observed"]))
