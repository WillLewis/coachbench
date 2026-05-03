from __future__ import annotations

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.action_legality import ActionValidationError, LegalActionEnumerator
from coachbench.engine import CoachBenchEngine
from coachbench.graph_loader import StrategyGraph
from coachbench.observations import defense_observation_before_play, offense_observation_before_play
from coachbench.schema import GameState
from coachbench.schema import AgentMemory, DefenseAction, OffenseAction


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
    offense_observation = offense_observation_before_play(GameState(), ["inside_zone"], {"spacing": 3})
    defense_observation = defense_observation_before_play(GameState(), ["base_cover3"], {"coverage": 3})

    assert "visible_defensive_shell" not in offense_observation
    assert "visible_offensive_shape" not in defense_observation
    assert offense_observation["legal_concepts"] == ["inside_zone"]
    assert defense_observation["legal_calls"] == ["base_cover3"]
    assert offense_observation["own_resource_remaining"] == {"spacing": 3}
    assert defense_observation["own_resource_remaining"] == {"coverage": 3}


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
    assert public_play["legal_action_sets"]
    assert public_play["resource_budget_snapshot"]
    assert public_play["validation_result"]["ok"] is True
    assert public_play["validation_result"]["offense"]["fallback_used"] is False
    assert public_play["validation_result"]["defense"]["fallback_used"] is False
    assert play_internal["legal_action_set_id"] == public_play["legal_action_set_id"]
    assert play_internal["legal_action_sets"] == public_play["legal_action_sets"]
    assert play_internal["resource_budget_snapshot"] == public_play["resource_budget_snapshot"]
    assert play_internal["validation_result"] == public_play["validation_result"]


def test_validation_rejects_tampered_action_fields_and_risk() -> None:
    legal = LegalActionEnumerator(StrategyGraph())
    bad_offense = OffenseAction(
        personnel_family="bears_real_team",
        formation_family="compact",
        motion_family="none",
        concept_family="bunch_mesh",
        protection_family="standard",
        risk_level="legendary",
        constraint_tag="legal:bunch_mesh",
    )
    reasons = legal.validate_offense_action_reasons(bad_offense)
    assert any("risk level" in reason for reason in reasons)
    assert any("personnel_family" in reason for reason in reasons)
    assert any("formation_family" in reason for reason in reasons)

    bad_defense = DefenseAction(
        personnel_family="fictional_nickel",
        front_family="bear",
        coverage_family="simulated_pressure",
        pressure_family="pressure",
        disguise_family="late",
        matchup_focus="red_zone_space",
        risk_level="legendary",
        constraint_tag="legal:simulated_pressure",
    )
    reasons = legal.validate_defense_action_reasons(bad_defense)
    assert any("risk level" in reason for reason in reasons)
    assert any("front_family" in reason for reason in reasons)


def test_drive_resources_reduce_legal_action_sets() -> None:
    legal = LegalActionEnumerator(StrategyGraph())
    depleted_offense = {"protection": 1, "spacing": 1, "deception": 0, "volatility": 1}
    depleted_defense = {"rush": 1, "coverage": 2, "box": 2, "disguise": 0}

    assert "inside_zone" in legal.legal_offense_concepts(depleted_offense)
    assert "bunch_mesh" not in legal.legal_offense_concepts(depleted_offense)
    assert "base_cover3" in legal.legal_defense_calls(depleted_defense)
    assert "simulated_pressure" not in legal.legal_defense_calls(depleted_defense)


def test_invalid_third_party_action_records_fallback_instead_of_crashing() -> None:
    class BadOffense:
        name = "Bad Offense"

        def choose_action(self, observation, memory: AgentMemory, legal):
            return OffenseAction(
                personnel_family="bears_real_team",
                formation_family="compact",
                motion_family="none",
                concept_family="bunch_mesh",
                protection_family="standard",
                risk_level="legendary",
                constraint_tag="bad",
            )

    replay = CoachBenchEngine(seed=5).run_drive(BadOffense(), AdaptiveDefense(), max_plays=1)
    validation = replay["plays"][0]["public"]["validation_result"]

    assert replay["score"]["invalid_action_count"] == 1
    assert validation["ok"] is False
    assert validation["offense"]["fallback_used"] is True
    assert validation["offense"]["reasons"]
    assert replay["plays"][0]["public"]["offense_action"]["constraint_tag"].startswith("legal:")


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
