from __future__ import annotations

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.action_legality import ActionValidationError, LegalActionEnumerator
from coachbench.engine import CoachBenchEngine
from coachbench.graph_loader import StrategyGraph
from coachbench.observations import defense_observation_before_play, offense_observation_before_play
from coachbench.schema import GameState
from coachbench.schema import AgentMemory, OffenseAction


def test_showcase_replay_is_deterministic() -> None:
    first = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    second = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    assert first == second
    assert first["plays"]
    assert "film_room" in first


def test_legal_action_enumerator_rejects_invalid_action() -> None:
    legal = LegalActionEnumerator(StrategyGraph())
    bad = OffenseAction(
        personnel_family="fictional_11",
        formation_family="compact",
        motion_family="none",
        concept_family="impossible_magic_play",
        protection_family="standard",
        risk_level="balanced",
        constraint_tag="bad",
    )
    try:
        legal.validate_offense_action(bad)
    except ActionValidationError:
        return
    raise AssertionError("Invalid action was not rejected")


def test_replay_has_no_hidden_seed_value() -> None:
    replay = CoachBenchEngine(seed=123).run_drive(AdaptiveOffense(), AdaptiveDefense())
    assert replay["metadata"]["seed_hash"]
    assert "seed" not in replay["metadata"]


def test_agent_legal_api_does_not_expose_graph() -> None:
    class InspectingOffense:
        name = "Inspecting Offense"

        def choose_action(self, observation, memory: AgentMemory, legal):
            assert not hasattr(legal, "graph")
            assert not hasattr(legal, "matching_interactions")
            assert callable(legal.legal_offense_concepts)
            assert callable(legal.build_offense_action)
            return legal.build_offense_action("inside_zone", "conservative")

    CoachBenchEngine(seed=9).run_drive(InspectingOffense(), AdaptiveDefense(), max_plays=1)


def test_replay_separates_public_side_observed_and_internal_fields() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    play = replay["plays"][0]

    assert set(play) == {"public", "offense_observed", "defense_observed", "engine_internal"}
    assert "offense_belief_after" not in play
    assert "defense_belief_after" not in play
    assert "belief_after" not in play["public"]
    assert "offense_belief_after" not in play["public"]
    assert "defense_belief_after" not in play["public"]
    assert "belief_after" in play["offense_observed"]
    assert "belief_after" in play["defense_observed"]
    assert "offense_belief_after" in play["engine_internal"]
    assert "defense_belief_after" in play["engine_internal"]


def test_pre_commit_observations_do_not_include_mock_alignment_signals() -> None:
    offense_observation = offense_observation_before_play(GameState(), ["inside_zone"])
    defense_observation = defense_observation_before_play(GameState(), ["base_cover3"])

    assert "visible_defensive_shell" not in offense_observation
    assert "visible_offensive_shape" not in defense_observation
    assert offense_observation["legal_concepts"] == ["inside_zone"]
    assert defense_observation["legal_calls"] == ["base_cover3"]


def test_replay_includes_episode_and_per_play_contract_fields() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    metadata = replay["metadata"]
    public_play = replay["plays"][0]["public"]
    play_internal = replay["plays"][0]["engine_internal"]

    assert metadata["start_yardline"] == 22
    assert metadata["max_plays"] == 8
    assert metadata["initial_down"] == 1
    assert metadata["initial_distance"] == 10
    assert metadata["score_mode"] == "red_zone_points"
    assert metadata["drive_terminal_condition"]
    assert public_play["legal_action_set_id"]
    assert public_play["resource_budget_snapshot"]
    assert public_play["validation_result"] == {"offense": "valid", "defense": "valid"}
    assert play_internal["legal_action_set_id"] == public_play["legal_action_set_id"]
    assert play_internal["resource_budget_snapshot"] == public_play["resource_budget_snapshot"]
    assert play_internal["validation_result"] == public_play["validation_result"]


def test_side_observations_filter_private_event_visibility() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    play = replay["plays"][0]

    public_tags = {event["tag"] for event in play["public"]["events"]}
    offense_tags = {event["tag"] for event in play["offense_observed"]["events"]}
    defense_tags = {event["tag"] for event in play["defense_observed"]["events"]}

    assert "front_strength_declared" in offense_tags
    assert "front_strength_declared" not in defense_tags
    assert "front_strength_declared" not in public_tags


def test_opponent_tendencies_are_event_derived_not_raw_calls() -> None:
    class InspectingOffense:
        name = "Inspecting Offense"

        def choose_action(self, observation, memory: AgentMemory, legal):
            assert "simulated_pressure" not in memory.opponent_visible_tendencies
            assert "bear_front" not in memory.opponent_visible_tendencies
            return legal.build_offense_action("screen", "balanced")

    CoachBenchEngine(seed=11).run_drive(InspectingOffense(), AdaptiveDefense(), max_plays=2)
