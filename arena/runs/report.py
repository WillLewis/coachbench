from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ARENA_KINDS = {"best_of_n", "gauntlet", "tournament"}


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _public_plays(replay: dict[str, Any]) -> list[dict[str, Any]]:
    return [play["public"] for play in replay.get("plays", [])]


def _top_concept(replay: dict[str, Any]) -> str:
    concepts = [
        play.get("offense_action", {}).get("concept_family")
        for play in _public_plays(replay)
        if play.get("offense_action", {}).get("concept_family")
    ]
    if not concepts:
        return ""
    return sorted(Counter(concepts).items(), key=lambda item: (-item[1], item[0]))[0][0]


def _winner_side(replay: dict[str, Any]) -> str:
    result = replay.get("score", {}).get("result")
    if result == "touchdown":
        return "offense"
    if result == "stopped":
        return "defense"
    return "draw"


def replay_match_summary(replay: dict[str, Any]) -> dict[str, Any]:
    plays = _public_plays(replay)
    return {
        "success_rate": _mean([1.0 if play.get("success") else 0.0 for play in plays]),
        "ev_delta": _mean([float(play.get("expected_value_delta", 0.0)) for play in plays]),
        "top_concept": _top_concept(replay),
    }


def match_from_replay(
    *,
    match_id: str,
    replay: dict[str, Any],
    seed: int,
    replay_url: str,
    film_room_url: str,
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "offense_label": replay["agents"]["offense"],
        "defense_label": replay["agents"]["defense"],
        "seed": int(seed),
        "winner_side": _winner_side(replay),
        "points": replay["score"]["points"],
        "summary": replay_match_summary(replay),
        "replay_url": replay_url,
        "film_room_url": film_room_url,
    }


def failed_match(
    *,
    match_id: str,
    offense_label: str,
    defense_label: str,
    seed: int,
    error: str,
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "offense_label": offense_label,
        "defense_label": defense_label,
        "seed": seed,
        "winner_side": "draw",
        "points": 0,
        "summary": {"success_rate": 0.0, "ev_delta": 0.0, "top_concept": ""},
        "replay_url": "",
        "film_room_url": "",
        "failed": True,
        "error": error,
    }


def aggregate_matches(matches: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [match for match in matches if not match.get("failed")]
    top_counts = Counter(match["summary"].get("top_concept", "") for match in completed)
    top_counts.pop("", None)
    total_top = sum(top_counts.values()) or 1
    return {
        "mean_points_per_drive": _mean([float(match["points"]) for match in completed]),
        "success_rate": _mean([float(match["summary"]["success_rate"]) for match in completed]),
        "ev_delta": _mean([float(match["summary"]["ev_delta"]) for match in completed]),
        "adaptation_latency": 0.0,
        "counter_success_rate": _mean([1.0 if match["winner_side"] == "defense" else 0.0 for match in completed]),
        "play_distribution_shift": {
            key: round(value / total_top, 4)
            for key, value in sorted(top_counts.items())
        },
    }


def build_report(job_id: str, kind: str, config: dict[str, Any], matches: list[dict[str, Any]]) -> dict[str, Any]:
    if kind not in ARENA_KINDS:
        raise ValueError("unknown arena report kind")
    return {
        "job_id": job_id,
        "kind": kind,
        "config": config,
        "matches": matches,
        "aggregate": aggregate_matches(matches),
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
