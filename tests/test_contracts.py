from __future__ import annotations

import json
import re
from pathlib import Path

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.contracts import (
    ContractValidationError,
    OBSERVATION_ALLOWED_FIELDS,
    validate_action_schema,
    validate_daily_slate_report,
    validate_film_room_is_event_derived,
    validate_match_matrix_report,
    validate_observation_safety,
    validate_replay_contract,
)
from coachbench.engine import CoachBenchEngine
from coachbench.film_room import build_film_room, film_room_note_for_event, film_room_tweak_for_card, headline_for_terminal
from coachbench.graph_loader import StrategyGraph
from coachbench.observations import (
    defense_observation_before_play,
    offense_observation_before_play,
    post_play_defense_observation,
    post_play_offense_observation,
    post_play_public_observation,
)
from coachbench.schema import AgentMemory, GameState
from scripts.run_daily_slate import defense_agent, offense_agent, slate_entries
from scripts.run_match_matrix import case_seed, matrix_questions


def test_generated_replay_satisfies_replay_contract() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())

    validate_replay_contract(replay)


def test_episode_example_documents_plan_4_1_fields() -> None:
    text = Path("docs/episode_example.md").read_text(encoding="utf-8")
    payload = json.loads(re.search(r"```json\n(.*?)\n```", text, flags=re.DOTALL).group(1))

    assert {
        "episode_id",
        "graph_version",
        "engine_version",
        "seed",
        "start_yardline",
        "max_plays",
        "down",
        "distance",
        "score_mode",
        "drive_terminal_condition",
    } <= set(payload)


def test_agent_garage_doc_lists_plan_5_2_controls() -> None:
    text = Path("docs/agent_garage.md").read_text(encoding="utf-8")

    for control in [
        "offensive archetype",
        "defensive archetype",
        "risk tolerance",
        "adaptation speed",
        "screen trigger confidence",
        "explosive-shot tolerance",
        "run/pass tendency",
        "disguise sensitivity",
        "pressure frequency",
        "counter-repeat tolerance",
    ]:
        assert control in text
    assert "pressure-punish threshold" not in text
    assert "resource conservation" not in text


def test_action_schema_validator_requires_contract_fields() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    action = dict(replay["plays"][0]["public"]["offense_action"])
    action.pop("risk_level")

    try:
        validate_action_schema(action, "offense")
    except ContractValidationError as exc:
        assert "risk_level" in str(exc)
    else:
        raise AssertionError("Invalid action schema was accepted")


def test_observation_safety_validator_rejects_hidden_fields() -> None:
    observation = {
        "play_index": 1,
        "yards_gained": 2,
        "success": True,
        "terminal": False,
        "terminal_reason": None,
        "events": [],
        "graph_card_ids": [],
        "next_state": {},
        "belief_after": {},
        "defense_action": {"coverage_family": "zero_pressure"},
    }

    try:
        validate_observation_safety(observation, "offense")
    except ContractValidationError as exc:
        assert "defense_action" in str(exc)
    else:
        raise AssertionError("Hidden opponent action was accepted in an observation")


def test_observation_builders_only_return_allowlisted_fields() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense(), max_plays=1)
    result = replay["plays"][0]["engine_internal"]
    graph = StrategyGraph()
    legal_sets = graph.constraints["drive_budgets"]

    pre_offense = offense_observation_before_play(GameState(), ["inside_zone"], legal_sets["offense"])
    pre_defense = defense_observation_before_play(GameState(), ["base_cover3"], legal_sets["defense"])

    # Re-run a real resolution object through the post-play builders.
    engine = CoachBenchEngine(seed=42)
    legal = engine.legal
    resolution = engine.resolution.resolve(
        GameState(),
        legal.build_offense_action(result["offense_action"]["concept_family"]),
        legal.build_defense_action(result["defense_action"]["coverage_family"]),
        AgentMemory(),
        AgentMemory(),
    )

    observations = [
        (pre_offense, OBSERVATION_ALLOWED_FIELDS["offense"]["pre_play"]),
        (pre_defense, OBSERVATION_ALLOWED_FIELDS["defense"]["pre_play"]),
        (post_play_offense_observation(resolution), OBSERVATION_ALLOWED_FIELDS["offense"]["post_play"]),
        (post_play_defense_observation(resolution), OBSERVATION_ALLOWED_FIELDS["defense"]["post_play"]),
        (post_play_public_observation(resolution), OBSERVATION_ALLOWED_FIELDS["public"]["post_play"]),
    ]

    for observation, allowed in observations:
        assert set(observation) <= allowed


def test_scoring_reports_satisfy_contracts() -> None:
    matrix_case = "A_static_offense_vs_A_static_defense"
    match_matrix_report = {
        "report_id": "team-interaction-matrix-v0",
        "seed_start": 42,
        "cases": [
            {
                "case": matrix_case,
                "seed": case_seed(42, matrix_case),
                "points": 0,
                "result": "stopped",
                "plays": 1,
                "film_room_headline": "Drive stopped",
                "turning_point": {
                    "play_index": 1,
                    "expected_value_delta": 0.0,
                    "graph_card_ids": [],
                    "metric": "largest_abs_expected_value_delta",
                },
            }
        ],
        "questions": [
            {
                "id": "adaptive_offense_lift_vs_same_defense",
                "question": "Does adaptive offense outperform static offense against the same defense?",
                "baseline_case": "A_static_offense_vs_A_static_defense",
                "comparison_case": "B_adaptive_offense_vs_A_static_defense",
                "metric": "points",
                "baseline_value": 0,
                "comparison_value": 0,
                "answer": "no",
            },
            {
                "id": "adaptive_defense_suppression_vs_same_offense",
                "question": "Does adaptive defense suppress static offense?",
                "baseline_case": "A_static_offense_vs_A_static_defense",
                "comparison_case": "A_static_offense_vs_B_adaptive_defense",
                "metric": "opponent_points",
                "baseline_value": 0,
                "comparison_value": 7,
                "answer": "no",
            },
            {
                "id": "adaptive_vs_adaptive_nontrivial_sequencing",
                "question": "Does adaptive-vs-adaptive produce nontrivial sequencing?",
                "baseline_case": None,
                "comparison_case": "B_adaptive_offense_vs_B_adaptive_defense",
                "metric": "turning_point_graph_cards",
                "baseline_value": None,
                "comparison_value": ["redzone.play_action_after_run_tendency.v1"],
                "answer": "yes",
            },
            {
                "id": "obvious_exploits_or_degenerate_strategies",
                "question": "Does the graph create obvious exploits or degenerate strategies?",
                "baseline_case": None,
                "comparison_case": "all_cases",
                "metric": "case_points",
                "baseline_value": None,
                "comparison_value": {"A_static_offense_vs_A_static_defense": 0},
                "answer": "needs_review",
            },
        ],
    }
    validate_match_matrix_report(match_matrix_report)

    slate = {
        "slate_id": "test-slate",
        "entries": [
            {"seed": 42, "matchup": {"offense": "adaptive", "defense": "static"}},
        ],
    }
    results = []
    for entry in slate_entries(slate):
        matchup = entry["matchup"]
        replay = CoachBenchEngine(seed=int(entry["seed"])).run_drive(
            offense_agent(matchup["offense"]),
            defense_agent(matchup["defense"]),
        )
        seed = int(entry["seed"])
        results.append({
            "seed": seed,
            "seed_hash": replay["metadata"]["seed_hash"],
            "matchup": matchup,
            "offense_label": offense_agent(matchup["offense"]).name,
            "defense_label": defense_agent(matchup["defense"]).name,
            "points": replay["score"]["points"],
            "result": replay["score"]["result"],
            "plays": len(replay["plays"]),
            "replay_path": f"data/daily_slate/replays/{slate['slate_id']}_{seed}.json",
            "film_room": replay["film_room"],
        })

    total_points = sum(item["points"] for item in results)
    validate_daily_slate_report({
        "slate_id": slate["slate_id"],
        "results": results,
        "summary": {
            "total_points": total_points,
            "average_points": round(total_points / len(results), 2),
            "touchdown_rate": round(sum(1 for item in results if item["result"] == "touchdown") / len(results), 4),
            "field_goal_rate": round(sum(1 for item in results if item["result"] == "field_goal") / len(results), 4),
            "stopped_rate": round(sum(1 for item in results if item["result"] == "stopped") / len(results), 4),
            "mean_plays_per_drive": round(sum(item["plays"] for item in results) / len(results), 2),
            "suggested_review": "Compare each agent across the fixed Daily Slate entries before treating one result as robust.",
        },
    })


def test_match_matrix_questions_answer_plan_9_3_without_implying_lift() -> None:
    results = [
        {
            "case": "A_static_offense_vs_A_static_defense",
            "points": 0,
            "turning_point": {"graph_card_ids": []},
        },
        {
            "case": "B_adaptive_offense_vs_A_static_defense",
            "points": 0,
            "turning_point": {"graph_card_ids": []},
        },
        {
            "case": "A_static_offense_vs_B_adaptive_defense",
            "points": 7,
            "turning_point": {"graph_card_ids": ["redzone.bunch_mesh_vs_match.v1"]},
        },
        {
            "case": "B_adaptive_offense_vs_B_adaptive_defense",
            "points": 7,
            "turning_point": {"graph_card_ids": ["redzone.play_action_after_run_tendency.v1"]},
        },
    ]

    questions = {item["id"]: item for item in matrix_questions(results)}

    assert questions["adaptive_offense_lift_vs_same_defense"]["answer"] == "no"
    assert questions["adaptive_defense_suppression_vs_same_offense"]["answer"] == "no"
    assert questions["adaptive_vs_adaptive_nontrivial_sequencing"]["answer"] == "yes"
    assert questions["obvious_exploits_or_degenerate_strategies"]["answer"] == "needs_review"


def test_film_room_notes_must_be_event_derived() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    replay["film_room"]["notes"] = ["Unsupported tactical claim."]

    try:
        validate_film_room_is_event_derived(replay)
    except ContractValidationError as exc:
        assert "Film Room note" in str(exc)
    else:
        raise AssertionError("Unsupported Film Room note was accepted")


def test_film_room_notes_must_reference_observed_card_ids() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    observed_card_ids = {
        event["graph_card_id"]
        for play in replay["plays"]
        for section in ("public", "offense_observed", "defense_observed")
        for event in play[section]["events"]
    }
    absent_card = next(card for card in StrategyGraph().interactions if card["id"] not in observed_card_ids)
    event = dict(absent_card["tactical_events"][0])
    event["graph_card_id"] = absent_card["id"]
    replay["film_room"]["notes"] = [film_room_note_for_event(event, absent_card)]

    try:
        validate_film_room_is_event_derived(replay)
    except ContractValidationError as exc:
        assert "Film Room note" in str(exc)
    else:
        raise AssertionError("Film Room note from an unobserved graph card was accepted")


def test_film_room_tweaks_must_be_graph_derived() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    replay["film_room"]["suggested_tweaks"] = ["Call more screens because they are clever."]

    try:
        validate_film_room_is_event_derived(replay)
    except ContractValidationError as exc:
        assert "Film Room tweak" in str(exc)
    else:
        raise AssertionError("Unsupported Film Room tweak was accepted")


def test_film_room_tweaks_must_reference_observed_card_ids() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    observed_card_ids = {
        event["graph_card_id"]
        for play in replay["plays"]
        for section in ("public", "offense_observed", "defense_observed")
        for event in play[section]["events"]
    }
    absent_card = next(card for card in StrategyGraph().interactions if card["id"] not in observed_card_ids)
    replay["film_room"]["suggested_tweaks"] = [film_room_tweak_for_card(absent_card)]

    try:
        validate_film_room_is_event_derived(replay)
    except ContractValidationError as exc:
        assert "Film Room tweak" in str(exc)
    else:
        raise AssertionError("Film Room tweak from an unobserved graph card was accepted")


def test_film_room_notes_use_graph_cards_not_agent_intent_claims() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    notes = replay["film_room"]["notes"]
    tweaks = replay["film_room"]["suggested_tweaks"]

    assert notes
    assert all(" - see " in note or note.startswith("No high-leverage") for note in notes)
    assert all("redzone." not in note for note in notes)
    assert all("treated a pressure look" not in note for note in notes)
    assert all("space behind the rush" not in note for note in notes)
    assert all("Daily Slate" not in tweak for tweak in tweaks)


def test_film_room_headline_uses_terminal_reason() -> None:
    assert headline_for_terminal(0, "turnover") == "Turnover"
    assert headline_for_terminal(0, "turnover_on_downs") == "Turnover on downs"
    assert headline_for_terminal(0, "max_plays_reached") == "Stopped - out of plays"


def test_film_room_turning_point_metric_is_declared() -> None:
    film_room = build_film_room(
        [
            {
                "public": {"play_index": 1, "terminal_reason": "max_plays_reached", "graph_card_ids": []},
                "engine_internal": {"expected_value_delta": -0.2},
                "offense_observed": {"events": []},
                "defense_observed": {"events": []},
            }
        ],
        points=0,
    )

    assert film_room["turning_point"]["metric"] == "largest_abs_expected_value_delta"


def test_validate_replay_contract_rejects_missing_top_level_partition() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    replay.pop("debug")

    try:
        validate_replay_contract(replay)
    except ContractValidationError as exc:
        assert "replay missing fields" in str(exc)
    else:
        raise AssertionError("Replay missing a top-level partition was accepted")


def test_validate_replay_contract_rejects_nonempty_debug_partition() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    replay["debug"] = {"fields": ["private_trace"]}

    try:
        validate_replay_contract(replay)
    except ContractValidationError as exc:
        assert "debug partition" in str(exc)
    else:
        raise AssertionError("Replay with nonempty debug partition was accepted")
