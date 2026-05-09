from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app


OFFENSE_CONFIG = {
    "agent_name": "Run Offense",
    "side": "offense",
    "access_tier": "declarative",
    "risk_tolerance": "medium",
    "red_zone": {"default": "quick_game"},
    "third_down": {"default": "quick_game"},
    "preferred_concepts": ["quick_game", "inside_zone", "rpo_glance"],
    "avoided_concepts": ["vertical_shot"],
    "adaptation_speed": 0.4,
    "tendency_break_rate": 0.1,
    "constraints": {"max_vertical_shot_rate": 0.0},
}

DEFENSE_CONFIG = {
    "agent_name": "Run Defense",
    "side": "defense",
    "access_tier": "declarative",
    "risk_tolerance": "medium",
    "red_zone": {"default": "redzone_bracket"},
    "third_down": {"default": "simulated_pressure"},
    "preferred_concepts": ["simulated_pressure", "cover3_match", "redzone_bracket"],
    "avoided_concepts": ["zero_pressure"],
    "adaptation_speed": 0.5,
    "tendency_break_rate": 0.1,
    "constraints": {},
}


def _create_draft(client: TestClient, name: str, side: str, config: dict) -> str:
    response = client.post(
        "/v1/drafts",
        json={
            "name": name,
            "side_eligibility": side,
            "tier": "declarative",
            "config_json": config,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["draft"]["id"]


def test_run_drive_route_writes_replay_and_lists_session(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    offense_id = _create_draft(client, "Run Offense", "offense", OFFENSE_CONFIG)
    defense_id = _create_draft(client, "Run Defense", "defense", DEFENSE_CONFIG)

    first = client.post(
        "/v1/runs/drive",
        json={"offense_draft_id": offense_id, "defense_draft_id": defense_id, "seed": 42, "max_plays": 4},
    )
    assert first.status_code == 201, first.text
    first_payload = first.json()
    assert first_payload["replay_url"] == f"/v1/runs/{first_payload['run_id']}/replay"
    assert first_payload["summary"]["plays"] <= 4
    assert client.get(first_payload["replay_url"]).status_code == 200

    sessions = client.get("/v1/sessions")
    assert sessions.status_code == 200
    assert sessions.json()["sessions"][0]["id"] == first_payload["run_id"]
    assert sessions.json()["sessions"][0]["status"] == "completed"

    second = client.post(
        "/v1/runs/drive",
        json={"offense_draft_id": offense_id, "defense_draft_id": defense_id, "seed": 42, "max_plays": 4},
    )
    assert second.status_code == 201, second.text
    first_bytes = (Path("data/local_runs") / f"{first_payload['run_id']}.json").read_bytes()
    second_bytes = (Path("data/local_runs") / f"{second.json()['run_id']}.json").read_bytes()
    assert first_bytes == second_bytes


def test_run_drive_rejects_wrong_side_draft(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    offense_id = _create_draft(client, "Run Offense", "offense", OFFENSE_CONFIG)
    response = client.post(
        "/v1/runs/drive",
        json={"offense_draft_id": offense_id, "defense_draft_id": offense_id, "seed": 42},
    )
    assert response.status_code == 422
