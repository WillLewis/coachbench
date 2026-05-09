from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app


OFFENSE_CONFIG = {
    "agent_name": "Draft Offense",
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


def test_draft_lifecycle_and_version_bump(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    create = client.post(
        "/v1/drafts",
        json={
            "name": "Draft Offense",
            "side_eligibility": "offense",
            "tier": "declarative",
            "config_json": OFFENSE_CONFIG,
        },
    )
    assert create.status_code == 201, create.text
    draft = create.json()["draft"]
    assert draft["version"] == 1

    listed = client.get("/v1/drafts")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["drafts"]] == [draft["id"]]

    fetched = client.get(f"/v1/drafts/{draft['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["draft"]["config_json"]["preferred_concepts"][0] == "quick_game"

    updated = client.patch(f"/v1/drafts/{draft['id']}", json={"name": "Draft Offense v2"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["draft"]["version"] == 2
    assert updated.json()["draft"]["name"] == "Draft Offense v2"

    deleted = client.delete(f"/v1/drafts/{draft['id']}")
    assert deleted.status_code == 200
    assert client.get(f"/v1/drafts/{draft['id']}").status_code == 404


def test_drafts_reject_invalid_config_before_persisting(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    invalid = dict(OFFENSE_CONFIG)
    invalid["preferred_concepts"] = ["unknown_concept"]
    response = client.post(
        "/v1/drafts",
        json={
            "name": "Bad Draft",
            "side_eligibility": "offense",
            "tier": "declarative",
            "config_json": invalid,
        },
    )
    assert response.status_code == 422
    assert client.get("/v1/drafts").json()["drafts"] == []
