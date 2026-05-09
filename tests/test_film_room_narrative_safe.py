from __future__ import annotations

import json
import re
from pathlib import Path

from coachbench.film_room import narrative_for_drive


BANNED = re.compile(r"seed|secret|api_key|admin|debug|Tier 0|Tier 1|Tier 2", re.IGNORECASE)


def test_narrative_contains_no_hidden_or_tier_tokens() -> None:
    replay = json.loads(Path("data/demo_replay.json").read_text(encoding="utf-8"))
    narrative = narrative_for_drive(replay["film_room"], replay["plays"])
    assert narrative
    assert not BANNED.search(narrative)
