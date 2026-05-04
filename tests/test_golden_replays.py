from __future__ import annotations

import json
from pathlib import Path

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.engine import CoachBenchEngine


def test_golden_replays_match_engine_output() -> None:
    manifest = json.loads(Path("data/golden_seeds/seeds.json").read_text(encoding="utf-8"))

    for item in manifest["seeds"]:
        seed = int(item["seed"])
        expected = json.loads(Path(f"data/golden_replays/{seed}.json").read_text(encoding="utf-8"))
        actual = CoachBenchEngine(seed=seed).run_drive(AdaptiveOffense(), AdaptiveDefense())

        assert actual == expected, (
            f"Golden replay drift on seed {seed}. Run `python "
            "scripts/regenerate_golden_replays.py` if this drift is intentional, "
            "then commit the updated files."
        )
