from __future__ import annotations

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.contracts import (
    ContractValidationError,
    validate_action_schema,
    validate_daily_slate_report,
    validate_film_room_is_event_derived,
    validate_match_matrix_report,
    validate_observation_safety,
    validate_replay_contract,
)
from coachbench.engine import CoachBenchEngine
from coachbench.film_room import build_film_room, headline_for_terminal
from scripts.run_daily_slate import defense_agent, offense_agent, slate_entries
from scripts.run_match_matrix import case_seed


def test_generated_replay_satisfies_replay_contract() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())

    validate_replay_contract(replay)


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
                "turning_point": {"play_index": 1},
            }
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
        results.append({
            "seed_hash": replay["metadata"]["seed_hash"],
            "matchup": matchup,
            "points": replay["score"]["points"],
            "result": replay["score"]["result"],
            "plays": len(replay["plays"]),
            "film_room": replay["film_room"],
        })

    validate_daily_slate_report({
        "slate_id": slate["slate_id"],
        "results": results,
        "summary": {
            "total_points": sum(item["points"] for item in results),
            "average_points": round(sum(item["points"] for item in results) / len(results), 2),
            "suggested_review": "Compare each agent across the fixed Daily Slate entries before treating one result as robust.",
        },
    })


def test_film_room_notes_must_be_event_derived() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    replay["film_room"]["notes"] = ["Unsupported tactical claim."]

    try:
        validate_film_room_is_event_derived(replay)
    except ContractValidationError as exc:
        assert "Film Room note" in str(exc)
    else:
        raise AssertionError("Unsupported Film Room note was accepted")


def test_film_room_notes_use_graph_cards_not_agent_intent_claims() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    notes = replay["film_room"]["notes"]
    tweaks = replay["film_room"]["suggested_tweaks"]

    assert notes
    assert all(note.startswith("Graph card \"") or note.startswith("No high-leverage") for note in notes)
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
