from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app, db
from arena.assistant.proposal import base_declarative_config
from arena.storage import drafts


ROOT = Path(__file__).resolve().parents[2]


def test_film_room_tweak_proposal_cites_real_replay_play(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_GLOBAL_KILL_SWITCH", "on")
    replay_dir = tmp_path / "ui/showcase_replays"
    replay_dir.mkdir(parents=True)
    shutil.copyfile(ROOT / "ui/showcase_replays/seed_42.json", replay_dir / "seed_42.json")

    draft = drafts.create_draft(
        db(),
        name="grounded-tweak",
        side_eligibility="offense",
        tier="declarative",
        config_json=base_declarative_config("offense"),
    )
    response = TestClient(app).post(
        "/v1/assistant/propose",
        json={
            "prompt": "",
            "context": {
                "request_type": "film_room_tweak",
                "current_draft_id": draft["id"],
                "current_run_id": "seed-42",
                "selected_play_index": 1,
                "session_id": "grounded-film-room",
            },
        },
    )

    assert response.status_code == 200, response.text
    proposal = response.json()["proposal"]
    assert proposal["intent"] == "tweak"
    film_refs = [ref for ref in proposal["evidence_refs"] if ref["type"] == "film_room_event"]
    assert film_refs
    replay = json.loads((ROOT / "ui/showcase_replays/seed_42.json").read_text(encoding="utf-8"))
    real_play_indices = {
        int(play.get("public", play).get("play_index"))
        for play in replay["plays"]
    }
    for ref in film_refs:
        assert ref["play_index"] in real_play_indices
