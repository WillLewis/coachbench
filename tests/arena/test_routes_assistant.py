from __future__ import annotations

from pathlib import Path
import shutil

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app


ROOT = Path(__file__).resolve().parents[2]


def _env(monkeypatch) -> None:
    monkeypatch.setenv("LLM_GLOBAL_KILL_SWITCH", "off")
    monkeypatch.setenv("LLM_MAX_CALLS_PER_SESSION", "50")
    monkeypatch.setenv("LLM_MAX_CALLS_PER_IP_WINDOW", "50")
    monkeypatch.setenv("LLM_IP_WINDOW_SECONDS", "3600")
    monkeypatch.setenv("LLM_MAX_CONCURRENT_SESSIONS", "1")
    monkeypatch.setenv("LLM_VIRAL_SPIKE_COST_CEILING_USD", "100")


def _copy_seed_replay(tmp_path: Path) -> None:
    out = tmp_path / "ui/showcase_replays"
    out.mkdir(parents=True)
    shutil.copyfile(ROOT / "ui/showcase_replays/seed_42.json", out / "seed_42.json")


def _propose(client: TestClient, prompt: str, context: dict | None = None):
    return client.post("/v1/assistant/propose", json={"prompt": prompt, "context": context or {"session_id": prompt[:8]}})


def _accept(client: TestClient, proposal: dict, name: str = "assistant-draft"):
    return client.post("/v1/assistant/accept", json={"proposal": proposal, "draft_name": name})


def test_assistant_routes_propose_accept_create_tweak_and_save_as_new(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _env(monkeypatch)
    client = TestClient(app)

    proposed = _propose(client, "Build an offense that punishes pressure without throwing picks.")
    assert proposed.status_code == 200, proposed.text
    proposal = proposed.json()["proposal"]
    assert proposal["intent"] == "create"

    accepted = _accept(client, proposal, "pressure-answer")
    assert accepted.status_code == 201, accepted.text
    draft = accepted.json()["draft"]
    assert draft["config_json"]["constraints"]["assistant_parameters"]["screen_trigger_confidence"] == 0.68

    tweak = _propose(
        client,
        "We got baited by simulated pressure. What should I change?",
        {"current_draft_id": draft["id"], "session_id": "tweak-session"},
    )
    assert tweak.status_code == 200, tweak.text
    tweak_proposal = tweak.json()["proposal"]
    assert tweak_proposal["intent"] == "tweak"
    updated = _accept(client, tweak_proposal, "unused")
    assert updated.status_code == 201, updated.text
    assert updated.json()["draft"]["version"] == 2

    save_copy = dict(tweak_proposal)
    save_copy["intent"] = "save_as_new"
    save_copy["proposed_changes"] = []
    saved = _accept(client, save_copy, "pressure-answer-copy")
    assert saved.status_code == 201, saved.text
    assert saved.json()["draft"]["id"] != draft["id"]


def test_assistant_routes_cover_free_text_identity_and_film_room(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _env(monkeypatch)
    _copy_seed_replay(tmp_path)
    client = TestClient(app)

    create = _propose(client, "Build an offense that punishes pressure without throwing picks.", {"session_id": "create"})
    draft = _accept(client, create.json()["proposal"], "film-room-draft").json()["draft"]

    free_text = _propose(client, "make the offense more aggressive in the red zone", {"session_id": "free"})
    assert free_text.status_code == 200
    assert free_text.json()["proposal"]["intent"] == "clarify"

    identity = _propose(client, "", {"request_type": "identity_selected", "selected_identity_id": "harbor_hawk", "session_id": "identity"})
    assert identity.status_code == 200
    assert identity.json()["proposal"]["intent"] == "clarify"

    film = _propose(
        client,
        "",
        {
            "request_type": "film_room_tweak",
            "current_draft_id": draft["id"],
            "current_run_id": "seed-42",
            "selected_play_index": 1,
            "session_id": "film",
        },
    )
    assert film.status_code == 200, film.text
    proposal = film.json()["proposal"]
    assert proposal["intent"] == "tweak"
    assert any(ref["type"] == "film_room_event" for ref in proposal["evidence_refs"])


def test_assistant_budget_gate_releases_concurrency(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _env(monkeypatch)
    client = TestClient(app)
    first = _propose(client, "Build an offense that punishes pressure without throwing picks.", {"session_id": "a"})
    second = _propose(client, "Build a run-first coordinator that unlocks play-action.", {"session_id": "b"})
    assert first.status_code == 200
    assert second.status_code == 200


def test_assistant_accept_rejects_clarify_and_invalid_claims(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _env(monkeypatch)
    client = TestClient(app)
    clarify = _propose(client, "something vague", {"session_id": "clarify"}).json()["proposal"]
    assert _accept(client, clarify).status_code == 422

    proposal = _propose(client, "Build an offense that punishes pressure without throwing picks.", {"session_id": "bad-identity"}).json()["proposal"]
    proposal["target_identity_id"] = "iron_veil"
    failed = _accept(client, proposal, "bad-identity")
    assert failed.status_code == 422

    tier_fail = _propose(client, "Build an offense that punishes pressure without throwing picks.", {"session_id": "bad-tier"}).json()["proposal"]
    tier_fail["target_tier"] = "prompt_policy"
    failed_tier = _accept(client, tier_fail, "bad-tier")
    assert failed_tier.status_code == 422
