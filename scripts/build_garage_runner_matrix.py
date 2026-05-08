from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import _path  # noqa: F401
except ModuleNotFoundError:
    from scripts import _path  # noqa: F401

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.contracts import validate_replay_contract
from coachbench.engine import CoachBenchEngine


DEFAULT_SEEDS = [6, 10, 42, 72, 99, 123]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _profile_config(profiles: dict[str, Any], group: str, key: str) -> dict[str, Any]:
    profile = dict(profiles[group][key])
    profile["profile_key"] = key
    return profile


def _seed_pack(path: Path | None) -> list[int]:
    if path and path.exists():
        payload = _load_json(path)
        seeds = [int(seed) for seed in payload.get("seeds", [])]
        if seeds:
            for seed in DEFAULT_SEEDS:
                if len(seeds) >= 6:
                    break
                if seed not in seeds:
                    seeds.append(seed)
            return seeds[:6]
    return list(DEFAULT_SEEDS)


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


def _resources_ok(replay: dict[str, Any]) -> bool:
    for play in replay.get("plays", []):
        snapshot = play.get("public", {}).get("resource_budget_snapshot", {})
        for key in ("offense_remaining", "defense_remaining"):
            if any(value < 0 for value in snapshot.get(key, {}).values()):
                return False
    return True


def _top_graph_event(replay: dict[str, Any]) -> str:
    events = [
        event
        for play in replay.get("plays", [])
        for event in play.get("public", {}).get("events", [])
        if event.get("description")
    ]
    if not events:
        return "No graph event fired"
    return events[0]["description"]


def _entry(
    *,
    offense_key: str,
    defense_key: str,
    seed: int,
    replay: dict[str, Any],
    out_dir: Path,
    ui_relative_prefix: str,
) -> dict[str, Any]:
    file_name = f"{offense_key}__{defense_key}__{seed}.json"
    replay_id = f"garage-{offense_key}--{defense_key}--{seed}"
    return {
        "id": replay_id,
        "path": f"{ui_relative_prefix}/{file_name}",
        "file": file_name,
        "offense_preset_id": offense_key,
        "defense_preset_id": defense_key,
        "seed": seed,
        "points": int(replay.get("score", {}).get("points", 0)),
        "result": replay.get("score", {}).get("result", "stopped"),
        "plays": len(replay.get("plays", [])),
        "top_graph_event": _top_graph_event(replay),
        "invalid_actions": _invalid_actions(replay),
        "resource_ok": _resources_ok(replay),
        "output_path": str(out_dir / file_name),
    }


def build_matrix(
    *,
    profiles_path: Path,
    out_dir: Path,
    seed_pack_path: Path | None,
    ui_relative_prefix: str,
) -> dict[str, Any]:
    profiles = _load_json(profiles_path)
    seeds = _seed_pack(seed_pack_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []

    for offense_key in sorted(profiles.get("offense_archetypes", {})):
        offense_profile = _profile_config(profiles, "offense_archetypes", offense_key)
        for defense_key in sorted(profiles.get("defense_archetypes", {})):
            defense_profile = _profile_config(profiles, "defense_archetypes", defense_key)
            for seed in seeds:
                replay = CoachBenchEngine(seed=seed).run_drive(
                    AdaptiveOffense(offense_profile),
                    AdaptiveDefense(defense_profile),
                    agent_garage_config={
                        "source": "agent_garage_runner_matrix_v1",
                        "offense_profile": offense_profile,
                        "defense_profile": defense_profile,
                        "runner_seed": seed,
                    },
                )
                validate_replay_contract(replay)
                file_name = f"{offense_key}__{defense_key}__{seed}.json"
                (out_dir / file_name).write_text(json.dumps(replay, indent=2) + "\n", encoding="utf-8")
                entries.append(
                    _entry(
                        offense_key=offense_key,
                        defense_key=defense_key,
                        seed=seed,
                        replay=replay,
                        out_dir=out_dir,
                        ui_relative_prefix=ui_relative_prefix,
                    )
                )

    index = {
        "matrix_id": "garage_runner_matrix_v1",
        "profiles_path": profiles_path.as_posix(),
        "seed_pack": seeds,
        "entries": entries,
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static Agent Garage runner replay matrix.")
    parser.add_argument("--profiles", type=Path, default=Path("agent_garage/profiles.json"))
    parser.add_argument("--seed-pack", type=Path, default=Path("tests/fixtures/garage_knob_seeds.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/garage_runner"))
    parser.add_argument("--ui-relative-prefix", default="../data/garage_runner")
    args = parser.parse_args()

    index = build_matrix(
        profiles_path=args.profiles,
        out_dir=args.out_dir,
        seed_pack_path=args.seed_pack,
        ui_relative_prefix=args.ui_relative_prefix.rstrip("/"),
    )
    print(f"Wrote {len(index['entries'])} garage runner replays to {args.out_dir}")


if __name__ == "__main__":
    main()
