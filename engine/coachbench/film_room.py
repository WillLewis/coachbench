from __future__ import annotations

from typing import Any, Dict, List


def build_film_room(play_results: List[Dict[str, Any]], points: int) -> Dict[str, Any]:
    if not play_results:
        return {
            "headline": "No plays were resolved.",
            "turning_point": None,
            "notes": [],
            "suggested_tweaks": [],
        }

    turning = max(play_results, key=lambda p: abs(float(p.get("expected_value_delta", 0.0))))
    tags = [event["tag"] for play in play_results for event in play.get("events", [])]
    notes: List[str] = []
    tweaks: List[str] = []

    if "screen_baited" in tags:
        notes.append("The offense treated a pressure look as a screen opportunity, but the defense had enough coverage/disguise resources to bait it.")
        tweaks.append("Lower screen trigger confidence until pressure is confirmed by multiple signals.")
    if "pressure_punished" in tags:
        notes.append("The offense successfully punished true pressure with space behind the rush.")
        tweaks.append("Keep pressure-punish calls available, but avoid repeating them after a failed attempt.")
    if "coverage_switch_stress" in tags:
        notes.append("Bunch/mesh created communication stress against match-style coverage.")
        tweaks.append("Increase bunch/mesh use when match coverage stress confidence rises.")
    if "wide_zone_constrained" in tags:
        notes.append("The defense used front strength to constrain outside-zone looks.")
        tweaks.append("Pair outside-zone tendency with play-action flood or bootleg counters.")
    if "underneath_space_taken" in tags:
        notes.append("The offense took underneath space conceded by safer coverage structure.")
        tweaks.append("If explosives are capped, increase efficient quick-game calls.")

    if not notes:
        notes.append("No high-leverage graph event dominated the drive; compare call sequencing and risk level across seeds.")
        tweaks.append("Run the same agent across the Daily Slate to check whether the result is robust.")

    headline = "Touchdown drive" if points >= 7 else "Field-position drive" if points == 3 else "Drive stopped"

    return {
        "headline": headline,
        "turning_point": {
            "play_index": turning.get("play_index"),
            "expected_value_delta": turning.get("expected_value_delta"),
            "graph_card_ids": turning.get("graph_card_ids", []),
        },
        "notes": notes,
        "suggested_tweaks": tweaks,
    }
