from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app


def _config(name: str, side: str) -> dict:
    if side == "offense":
        return {
            "agent_name": name,
            "side": "offense",
            "access_tier": "declarative",
            "risk_tolerance": "medium",
            "red_zone": {"default": "quick_game"},
            "third_down": {"default": "quick_game"},
            "preferred_concepts": ["quick_game", "inside_zone"],
            "avoided_concepts": ["vertical_shot"],
            "adaptation_speed": 0.4,
            "tendency_break_rate": 0.1,
            "constraints": {"max_vertical_shot_rate": 0.0},
        }
    return {
        "agent_name": name,
        "side": "defense",
        "access_tier": "declarative",
        "risk_tolerance": "medium",
        "red_zone": {"default": "redzone_bracket"},
        "third_down": {"default": "simulated_pressure"},
        "preferred_concepts": ["simulated_pressure", "cover3_match"],
        "avoided_concepts": ["zero_pressure"],
        "adaptation_speed": 0.4,
        "tendency_break_rate": 0.1,
        "constraints": {},
    }


def _draft(client: TestClient, name: str, side: str) -> str:
    response = client.post(
        "/v1/drafts",
        json={
            "name": name,
            "side_eligibility": side,
            "tier": "declarative",
            "config_json": _config(name, side),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["draft"]["id"]


def test_same_drafts_and_seed_produce_byte_identical_replay_json(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    offense_id = _draft(client, "Stable Offense", "offense")
    defense_id = _draft(client, "Stable Defense", "defense")
    payload = {"offense_draft_id": offense_id, "defense_draft_id": defense_id, "seed": 99, "max_plays": 5}

    first = client.post("/v1/runs/drive", json=payload)
    second = client.post("/v1/runs/drive", json=payload)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    first_path = Path("data/local_runs") / f"{first.json()['run_id']}.json"
    second_path = Path("data/local_runs") / f"{second.json()['run_id']}.json"
    assert first_path.read_bytes() == second_path.read_bytes()
