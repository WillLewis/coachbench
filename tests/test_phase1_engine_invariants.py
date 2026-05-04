from __future__ import annotations

from agents.adaptive_defense import AdaptiveDefense
from agents.static_defense import StaticDefense
from coachbench.action_legality import LegalActionEnumerator
from coachbench.contracts import validate_action_schema
from coachbench.engine import CoachBenchEngine
from coachbench.graph_loader import StrategyGraph
from coachbench.resolution_engine import ResolutionEngine
from coachbench.schema import AgentMemory, OffenseAction


class BadOffense:
    name = "Bad Offense"

    def choose_action(self, observation, memory: AgentMemory, legal):
        return OffenseAction(
            personnel_family="invalid_personnel",
            formation_family="compact",
            motion_family="none",
            concept_family="bunch_mesh",
            protection_family="standard",
            risk_level="legendary",
            constraint_tag="bad",
        )


class AlwaysBunchOffense:
    name = "Always Bunch Offense"

    def choose_action(self, observation, memory: AgentMemory, legal):
        return OffenseAction(
            personnel_family="fictional_11",
            formation_family="bunch",
            motion_family="none",
            concept_family="bunch_mesh",
            protection_family="standard",
            risk_level="balanced",
            constraint_tag="legal:bunch_mesh",
        )


def test_invalid_actions_fallback_before_resolution(monkeypatch) -> None:
    graph = StrategyGraph()
    legal = LegalActionEnumerator(graph)
    received = []
    original_resolve = ResolutionEngine.resolve

    def recording_resolve(self, state, offense_action, defense_action, offense_memory, defense_memory):
        received.append((offense_action, defense_action))
        return original_resolve(self, state, offense_action, defense_action, offense_memory, defense_memory)

    monkeypatch.setattr(ResolutionEngine, "resolve", recording_resolve)
    replay = CoachBenchEngine(seed=5, graph=graph).run_drive(BadOffense(), AdaptiveDefense(), max_plays=1)

    assert replay["score"]["invalid_action_count"] == 1
    assert received
    for offense_action, defense_action in received:
        validate_action_schema(offense_action.to_dict(), "offense")
        validate_action_schema(defense_action.to_dict(), "defense")
        legal.validate_offense_action(offense_action)
        legal.validate_defense_action(defense_action)


def test_resource_impossible_submitted_action_falls_back_before_resolution() -> None:
    graph = StrategyGraph()
    legal = LegalActionEnumerator(graph)
    replay = CoachBenchEngine(seed=42, graph=graph).run_drive(
        AlwaysBunchOffense(),
        StaticDefense(),
        max_plays=12,
        start_yardline=99,
    )

    invalid_play = next(play for play in replay["plays"] if not play["public"]["validation_result"]["offense"]["ok"])
    public = invalid_play["public"]
    remaining_before = public["resource_budget_snapshot"]["offense_before"]
    legal_at_play = legal.legal_offense_concepts(remaining_before)

    assert "bunch_mesh" not in legal_at_play
    assert public["validation_result"]["offense"]["fallback_used"] is True
    assert public["offense_action"]["concept_family"] in legal_at_play


def test_replay_events_only_reference_declared_graph_cards() -> None:
    graph = StrategyGraph()
    graph_ids = {card["id"] for card in graph.interactions}
    replay = CoachBenchEngine(seed=42, graph=graph).run_drive(AlwaysBunchOffense(), StaticDefense(), max_plays=4)
    replay_card_ids = set()

    for play in replay["plays"]:
        for partition in ("public", "offense_observed", "defense_observed", "engine_internal"):
            for event in play[partition].get("events", []):
                assert event["graph_card_id"] in graph_ids
                replay_card_ids.add(event["graph_card_id"])

    assert replay_card_ids <= graph_ids
