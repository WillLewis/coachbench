from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_GENERATED_AT = "2026-05-06T00:00:00Z"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path, *, out_parent: Path, data_dir: Path, ui_dir: Path) -> str:
    if path == data_dir / "demo_replay.json":
        return "demo_replay.json"
    if path == ui_dir / "static_proof_replay.json":
        return "static_proof_replay.json"
    return Path("..", path.relative_to(out_parent.parent)).as_posix() if path.is_relative_to(out_parent.parent) else path.as_posix()


def _replay_id(path: Path, replay: dict[str, Any]) -> str:
    if path.name == "demo_replay.json":
        return "seed-42"
    if path.name == "static_proof_replay.json" or replay.get("metadata", {}).get("mode") == "static_proof":
        return "static-proof"
    match = re.search(r"seed[_-](\d+)", path.stem)
    if match:
        return f"seed-{match.group(1)}"
    return path.stem.removesuffix("_replay").replace("_", "-")


def _seed_value(replay_id: str) -> int:
    match = re.match(r"seed-(\d+)$", replay_id)
    return int(match.group(1)) if match else 0


def _invalid_actions(replay: dict[str, Any]) -> int:
    total = 0
    for play in replay.get("plays", []):
        result = play.get("public", {}).get("validation_result", {})
        if result.get("ok") is False:
            total += 1
        for side in ("offense", "defense"):
            side_result = result.get(side)
            if isinstance(side_result, dict) and side_result.get("fallback_used"):
                total += 1
    return total


def _sparkline(replay: dict[str, Any]) -> list[int]:
    points = []
    for play in replay.get("plays", []):
        next_state = play.get("public", {}).get("next_state", {})
        points.append(int(next_state.get("points", replay.get("score", {}).get("points", 0))))
    return points or [int(replay.get("score", {}).get("points", 0))]


def _top_graph_event(replay: dict[str, Any]) -> str:
    events = [
        event
        for play in replay.get("plays", [])
        for event in play.get("public", {}).get("events", [])
        if event.get("description")
    ]
    if not events:
        return "No graph event fired"
    return max(events, key=lambda event: len(str(event.get("counters", []))))["description"]


def _descriptor(path: Path, replay: dict[str, Any], *, out_parent: Path, data_dir: Path, ui_dir: Path) -> dict[str, Any]:
    replay_id = _replay_id(path, replay)
    points = int(replay.get("score", {}).get("points", 0))
    opponent_points = 0
    score_result = replay.get("score", {}).get("result", "stopped")
    converted = points > 0
    agents = replay.get("agents", {})
    return {
        "id": replay_id,
        "path": _display_path(path, out_parent=out_parent, data_dir=data_dir, ui_dir=ui_dir),
        "matchup": "Team A vs Team B",
        "seed": _seed_value(replay_id),
        "result": f"Team A {points} — Team B {opponent_points}",
        "outcome_chip": "Team A converted drive" if converted else "Team B stopped drive",
        "plays": len(replay.get("plays", [])),
        "top_graph_event": _top_graph_event(replay),
        "invalid_actions": _invalid_actions(replay),
        "tier_offense": 0,
        "tier_defense": 0,
        "offense_label": agents.get("offense", "Team A coordinator agent"),
        "defense_label": agents.get("defense", "Team B coordinator agent"),
        "sparkline": _sparkline(replay),
        "generated_at": replay.get("metadata", {}).get("generated_at", DEFAULT_GENERATED_AT),
        "terminal_result": score_result,
    }


def build_index(data_dir: Path, ui_dir: Path, out_path: Path) -> list[dict[str, Any]]:
    out_parent = out_path.parent
    replay_paths = sorted(data_dir.glob("*_replay.json"))
    static_proof = ui_dir / "static_proof_replay.json"
    if static_proof.exists():
        replay_paths.append(static_proof)
    descriptors = [
        _descriptor(path, _read_json(path), out_parent=out_parent, data_dir=data_dir, ui_dir=ui_dir)
        for path in replay_paths
    ]
    priority = {"seed-42": 0, "static-proof": 1}
    return sorted(descriptors, key=lambda item: (priority.get(item["id"], 2), item["id"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static UI replay index.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--ui-dir", type=Path, default=Path("ui"))
    parser.add_argument("--out", type=Path, default=Path("ui/replay_index.json"))
    args = parser.parse_args()

    index = build_index(args.data_dir, args.ui_dir, args.out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
