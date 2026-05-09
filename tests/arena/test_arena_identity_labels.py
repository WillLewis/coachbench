from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app
from arena.worker.main import process_one


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


def _draft(client: TestClient, name: str, side: str, identity_id: str | None = None) -> str:
    response = client.post(
        "/v1/drafts",
        json={
            "name": name,
            "side_eligibility": side,
            "tier": "declarative",
            "identity_id": identity_id,
            "config_json": _config(name, side),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["draft"]["id"]


def test_arena_uses_identity_label_and_preserves_technical_label(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    offense = _draft(client, "Technical Offense", "offense", "cinder_flash")
    defense = _draft(client, "Technical Defense", "defense")

    response = client.post(
        "/v1/arena/best_of_n",
        json={"offense_draft_id": offense, "defense_draft_id": defense, "n": 1, "seed_pack": [42], "max_plays": 4},
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    assert process_one()

    sessions = client.get("/v1/arena/sessions").json()["sessions"]
    assert sessions[0]["offense_label"] == "Cinder Flash"
    assert sessions[0]["defense_label"] == "Technical Defense"
    assert sessions[0]["offense_technical_label"] == "Technical Offense"

    report = client.get(f"/v1/arena/jobs/{job_id}/report").json()
    match = report["matches"][0]
    assert match["offense_label"] == "Cinder Flash"
    assert match["defense_label"] == "Technical Defense"
    assert match["technical_label"] == {
        "offense": "Technical Offense",
        "defense": "Technical Defense",
    }


def test_identity_routes_return_launch_identities(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    listed = client.get("/v1/identities")
    assert listed.status_code == 200
    assert {item["id"] for item in listed.json()["identities"]} >= {"cinder_flash", "harbor_hawk"}
    one = client.get("/v1/identities/cinder_flash")
    assert one.status_code == 200
    assert one.json()["identity"]["display_name"] == "Cinder Flash"
