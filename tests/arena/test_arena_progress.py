from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app
from arena.worker.main import process_one


def _config(name: str, side: str) -> dict:
    base = {
        "agent_name": name,
        "side": side,
        "access_tier": "declarative",
        "risk_tolerance": "medium",
        "red_zone": {"default": "quick_game" if side == "offense" else "redzone_bracket"},
        "third_down": {"default": "quick_game" if side == "offense" else "simulated_pressure"},
        "adaptation_speed": 0.4,
        "tendency_break_rate": 0.1,
        "constraints": {},
    }
    if side == "offense":
        base.update({"preferred_concepts": ["quick_game"], "avoided_concepts": ["vertical_shot"]})
    else:
        base.update({"preferred_concepts": ["simulated_pressure"], "avoided_concepts": ["zero_pressure"]})
    return base


def _draft(client: TestClient, name: str, side: str) -> str:
    response = client.post(
        "/v1/drafts",
        json={"name": name, "side_eligibility": side, "tier": "declarative", "config_json": _config(name, side)},
    )
    assert response.status_code == 201, response.text
    return response.json()["draft"]["id"]


def test_arena_progress_advances_and_failed_match_is_reported(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    offense = _draft(client, "Progress Offense", "offense")
    defense = _draft(client, "Progress Defense", "defense")
    wrong_side = _draft(client, "Wrong Side Offense", "offense")

    response = client.post(
        "/v1/arena/gauntlet",
        json={"draft_id": offense, "draft_side": "offense", "opponent_pool": [defense, wrong_side], "seed_pack": [42], "max_plays": 3},
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]

    before = client.get(f"/v1/arena/jobs/{job_id}").json()
    assert before["completed_runs"] == 0
    assert before["total_runs"] == 2

    assert process_one()
    after = client.get(f"/v1/arena/jobs/{job_id}").json()
    assert after["completed_runs"] == 2
    assert after["failed_runs"] == 1
    assert after["completed_runs"] >= before["completed_runs"]

    report = client.get(f"/v1/arena/jobs/{job_id}/report").json()
    failed = [match for match in report["matches"] if match.get("failed")]
    assert len(failed) == 1
    assert "defense_draft_id" in failed[0]["error"]
