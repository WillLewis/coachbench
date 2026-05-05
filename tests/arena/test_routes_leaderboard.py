from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.deps import ADMIN_TOKEN
from arena.api.app import app, db
from arena.storage.leaderboard import add_run


def test_leaderboard_routes_hide_tier3_publicly(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    create = client.post(
        "/v1/admin/seasons",
        json={"label": "Local", "seeds": [42], "max_plays": 8, "opponent_kind": "static"},
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    assert create.status_code == 201, create.text
    season_id = create.json()["season_id"]
    add_run(db(), season_id, "agent", 42, 7, "touchdown", 3, "sandboxed_code")
    public = client.get(f"/v1/seasons/{season_id}/leaderboard")
    admin = client.get(f"/v1/seasons/{season_id}/leaderboard", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert public.status_code == 200
    assert public.json()["standings"] == []
    assert admin.json()["standings"][0]["agent_id"] == "agent"
    assert "42" not in public.text
    assert "42" not in admin.text


def test_leaderboard_run_route_enqueues_job(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    season = client.post(
        "/v1/admin/seasons",
        json={"label": "Local", "seeds": [42], "max_plays": 8, "opponent_kind": "static"},
        headers={"X-Admin-Token": ADMIN_TOKEN},
    ).json()["season_id"]
    response = client.post(f"/v1/admin/seasons/{season}/run", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert response.status_code == 202
    assert response.json()["job_id"]


def test_runs_route_hides_non_admin_runs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    season = client.post(
        "/v1/admin/seasons",
        json={"label": "Local", "seeds": [42], "max_plays": 8, "opponent_kind": "static"},
        headers={"X-Admin-Token": ADMIN_TOKEN},
    ).json()["season_id"]
    add_run(db(), season, "agent", 42, 7, "touchdown", 3, "sandboxed_code")
    assert client.get(f"/v1/seasons/{season}/runs/agent").json()["runs"] == []
    assert client.get(f"/v1/seasons/{season}/runs/agent", headers={"X-Admin-Token": ADMIN_TOKEN}).json()["runs"]
