from __future__ import annotations

import json
from pathlib import Path

from coachbench.film_room import narrative_for_drive


def test_narrative_is_byte_deterministic_for_same_replay() -> None:
    replay = json.loads(Path("ui/showcase_replays/seed_42.json").read_text(encoding="utf-8"))
    outputs = [narrative_for_drive(replay["film_room"], replay["plays"]) for _ in range(10)]
    assert len(set(outputs)) == 1
