from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from agents.static_defense import StaticDefense
from arena.api.app import app, db
from arena.tiers.base import SanitizedObservation
from arena.tiers.bridge import TieredAgent
from arena.tiers.declarative import Tier0Adapter, load_tier0_config
from arena.tiers.prompt_policy import Tier1Adapter, load_tier1_config
from arena.tiers.remote_endpoint import Tier2Adapter, Tier2Config
from arena.tiers.sanitized_observation import build_tier_observation
from coachbench.contracts import HIDDEN_OBSERVATION_FIELDS
from coachbench.engine import CoachBenchEngine
from coachbench.schema import AgentMemory

ROOT = Path(__file__).resolve().parents[2]


class IllegalTier1:
    access_tier = "prompt_policy"
    name = "Illegal Tier 1"

    def choose_action(self, obs):
        return "not_legal"


def _obs() -> SanitizedObservation:
    return SanitizedObservation("offense", {"down": 1, "yardline": 12}, ["quick_game", "screen"], {}, {"own_recent_calls": [], "opponent_visible_tendencies": {}, "beliefs": {}})


def _tier2_agent(handler) -> TieredAgent:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = Tier2Adapter(Tier2Config("Remote", "offense", "remote_endpoint"), "https://example.invalid/agent", http_client=client, agent_id="remote")
    return TieredAgent(adapter, "offense")


def test_illegal_tier1_and_tier2_actions_fall_back_deterministically() -> None:
    tier1 = TieredAgent(IllegalTier1(), "offense")
    replay = CoachBenchEngine(seed=42).run_drive(tier1, StaticDefense(), max_plays=1)
    assert replay["plays"][0]["public"]["offense_action"]["constraint_tag"].startswith("legal:")
    assert tier1.fallback_count == 1

    tier2 = _tier2_agent(lambda request: httpx.Response(200, json={"action": "not_legal"}))
    replay = CoachBenchEngine(seed=42).run_drive(tier2, StaticDefense(), max_plays=1)
    assert replay["plays"][0]["public"]["offense_action"]["constraint_tag"].startswith("legal:")
    assert tier2.adapter.fallback_reasons[-1] == "tier2_invalid_action"


def test_sanitized_observation_for_each_public_tier_has_no_hidden_keys() -> None:
    raw = {
        "game_state": {"down": 1, "distance": 10, "yardline": 20, "play_index": 0, "points": 0, "max_plays": 8, "seed": 42},
        "own_resource_remaining": {"spacing": 10},
        "seed": 42,
        "seed_hash": "hidden",
        "legal_action_set_id": "hidden",
        "resource_budget_snapshot": {"offense_before": {"spacing": 10}},
    }
    for _tier in ("declarative", "prompt_policy", "remote_endpoint"):
        obs = build_tier_observation("offense", raw, AgentMemory(), ["quick_game"], {"spacing": 10})
        encoded = repr(obs)
        for key in HIDDEN_OBSERVATION_FIELDS | {"seed", "seed_hash", "legal_action_set_id", "resource_budget_snapshot"}:
            assert key not in encoded


def test_public_leaderboard_and_run_responses_never_include_raw_seeds(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    season = client.post(
        "/v1/admin/seasons",
        headers={"X-Admin-Token": __import__("arena.api.deps", fromlist=["ADMIN_TOKEN"]).ADMIN_TOKEN},
        json={"label": "Rookie", "seeds": [42], "max_plays": 8, "opponent_kind": "static", "league": "rookie"},
    ).json()["season_id"]
    leaderboard = client.get(f"/v1/seasons/{season}/leaderboard")
    runs = client.get(f"/v1/seasons/{season}/runs/agent")
    assert "42" not in leaderboard.text
    assert "42" not in runs.text


def test_illegal_tier2_action_never_reaches_resolution(monkeypatch) -> None:
    seen = []
    from coachbench.resolution_engine import ResolutionEngine

    original = ResolutionEngine.resolve

    def record(self, state, offense_action, defense_action, *args, **kwargs):
        seen.append(offense_action.concept_family)
        return original(self, state, offense_action, defense_action, *args, **kwargs)

    monkeypatch.setattr(ResolutionEngine, "resolve", record)
    tier2 = _tier2_agent(lambda request: httpx.Response(200, json={"action": "not_legal"}))
    CoachBenchEngine(seed=42).run_drive(tier2, StaticDefense(), max_plays=1)
    assert seen
    assert "not_legal" not in seen


def test_tier2_response_cannot_mutate_engine_state() -> None:
    tier2 = _tier2_agent(lambda request: httpx.Response(200, json={"action": "screen", "next_state": {"points": 99}, "debug": {"seed": 42}}))
    replay = CoachBenchEngine(seed=42).run_drive(tier2, StaticDefense(), max_plays=1)
    assert replay["plays"][0]["public"]["next_state"]["points"] != 99


def test_tier2_timeout_returns_before_hard_cap() -> None:
    tier2 = _tier2_agent(lambda request: (_ for _ in ()).throw(httpx.TimeoutException("slow")))
    start = time.monotonic()
    replay = CoachBenchEngine(seed=42).run_drive(tier2, StaticDefense(), max_plays=1)
    elapsed = time.monotonic() - start
    assert elapsed < 2.0
    assert replay["plays"][0]["public"]["offense_action"]["constraint_tag"].startswith("legal:")


def test_tier0_and_tier1_same_seed_replays_are_identical() -> None:
    tier0 = load_tier0_config(ROOT / "data/agent_configs/tier0_efficiency_optimizer.json")
    tier1 = load_tier1_config(ROOT / "data/agent_configs/tier1_constraint_setter.json")
    for factory in (
        lambda: TieredAgent(Tier0Adapter(tier0), "offense"),
        lambda: TieredAgent(Tier1Adapter(tier1), "offense"),
    ):
        replay_a = CoachBenchEngine(seed=42).run_drive(factory(), StaticDefense(), max_plays=3)
        replay_b = CoachBenchEngine(seed=42).run_drive(factory(), StaticDefense(), max_plays=3)
        assert replay_a == replay_b


def test_public_agent_cards_do_not_leak_admin_or_secret_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    created = client.post(
        "/v1/agents",
        data={
            "access_tier": "remote_endpoint",
            "name": "remote_agent",
            "version": "v1",
            "label": "Remote Agent",
            "side": "offense",
            "owner_id": "owner",
            "endpoint_url": "https://example.invalid/agent",
            "api_key": "secret",
        },
        files={"meta": ("meta.txt", b"", "text/plain")},
    )
    agent_id = created.json()["agent_id"]
    card = client.get(f"/v1/agents/{agent_id}")
    assert card.status_code == 200
    text = json.dumps(card.json())
    for forbidden in ("endpoint_url", "api_key", "qualification_report_path", "banned_reason", "source_path", "seed", "endpoint_url_hash"):
        assert forbidden not in text
