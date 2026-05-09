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


def _run_job(client: TestClient, job_id: str) -> dict:
    assert process_one()
    status = client.get(f"/v1/arena/jobs/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "done"
    report = client.get(f"/v1/arena/jobs/{job_id}/report")
    assert report.status_code == 200, report.text
    payload = report.json()
    assert {"job_id", "kind", "config", "matches", "aggregate"} <= set(payload)
    assert payload["matches"]
    assert {"mean_points_per_drive", "success_rate", "ev_delta"} <= set(payload["aggregate"])
    assert payload["matches"][0]["replay_url"].startswith("/v1/replays/")
    assert payload["matches"][0]["film_room_url"].endswith("/film_room")
    return payload


def test_arena_routes_enqueue_and_report_all_job_types(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    offense = _draft(client, "Arena Offense", "offense")
    defense = _draft(client, "Arena Defense", "defense")
    defense_two = _draft(client, "Arena Defense Two", "defense")

    best = client.post(
        "/v1/arena/best_of_n",
        json={"offense_draft_id": offense, "defense_draft_id": defense, "n": 2, "seed_pack": [42, 99], "max_plays": 4},
    )
    assert best.status_code == 202, best.text
    best_report = _run_job(client, best.json()["job_id"])
    assert best_report["kind"] == "best_of_n"
    assert len(best_report["matches"]) == 2

    gauntlet = client.post(
        "/v1/arena/gauntlet",
        json={"draft_id": offense, "draft_side": "offense", "opponent_pool": [defense, defense_two], "seed_pack": [42], "max_plays": 4},
    )
    assert gauntlet.status_code == 202, gauntlet.text
    gauntlet_report = _run_job(client, gauntlet.json()["job_id"])
    assert gauntlet_report["kind"] == "gauntlet"
    assert len(gauntlet_report["matches"]) == 2

    tournament = client.post(
        "/v1/arena/tournament",
        json={
            "participant_draft_ids": [offense, defense],
            "side_assignments": {offense: "offense", defense: "defense"},
            "seed_pack": [42],
            "format": "round_robin",
            "max_plays": 4,
        },
    )
    assert tournament.status_code == 202, tournament.text
    tournament_report = _run_job(client, tournament.json()["job_id"])
    assert tournament_report["kind"] == "tournament"
    assert len(tournament_report["matches"]) == 1

    sessions = client.get("/v1/arena/sessions")
    assert sessions.status_code == 200
    assert sessions.json()["sessions"]
