from __future__ import annotations

import json
from pathlib import Path

try:
    import _path  # noqa: F401
except ModuleNotFoundError:
    from scripts import _path  # noqa: F401

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.engine import CoachBenchEngine


SEEDS_PATH = Path("data/golden_seeds/seeds.json")
OUT_DIR = Path("data/golden_replays")


def main() -> None:
    manifest = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    changed = []

    for item in manifest["seeds"]:
        seed = int(item["seed"])
        out = OUT_DIR / f"{seed}.json"
        replay = CoachBenchEngine(seed=seed).run_drive(AdaptiveOffense(), AdaptiveDefense())
        payload = json.dumps(replay, indent=2) + "\n"
        before = out.read_text(encoding="utf-8") if out.exists() else None
        out.write_text(payload, encoding="utf-8")
        if before != payload:
            changed.append(str(out))

    if changed:
        print("Changed golden replays:")
        for path in changed:
            print(f"- {path}")
    else:
        print("Golden replays unchanged.")


if __name__ == "__main__":
    main()
