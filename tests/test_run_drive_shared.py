from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app


ROOT = Path(__file__).resolve().parents[1]


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
        json={"name": name, "side_eligibility": side, "tier": "declarative", "config_json": _config(name, side)},
    )
    assert response.status_code == 201, response.text
    return response.json()["draft"]["id"]


def test_cli_arena_mode_and_http_route_share_drive_results(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    offense = _draft(client, "Shared Offense", "offense")
    defense = _draft(client, "Shared Defense", "defense")

    route = client.post(
        "/v1/runs/drive",
        json={"offense_draft_id": offense, "defense_draft_id": defense, "seed": 42, "max_plays": 4},
    )
    assert route.status_code == 201, route.text

    out = tmp_path / "cli_report.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_best_of_n.py"),
            "--offense-draft-id",
            offense,
            "--defense-draft-id",
            defense,
            "--db-path",
            str(tmp_path / "arena/storage/local/arena.sqlite3"),
            "--job-id",
            "shared-cli",
            "--seeds",
            "42",
            "--max-plays",
            "4",
            "--out",
            str(out),
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        timeout=30,
    )

    report = json.loads(out.read_text(encoding="utf-8"))
    match = report["matches"][0]
    assert match["points"] == route.json()["summary"]["points"]
    assert match["summary"]["top_concept"]
