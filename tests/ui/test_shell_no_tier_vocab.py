from __future__ import annotations

import re
from pathlib import Path


SHELL_FILES = [
    Path("ui/app.html"),
    Path("ui/app.js"),
    Path("ui/topbar.js"),
    Path("ui/left_rail.js"),
]
BANNED = re.compile(r"Tier 0|Tier 1|Tier 2|PHASE 2|LLM AGENTS")


def test_unified_shell_has_no_launch_tier_vocabulary() -> None:
    offenders = {
        str(path): BANNED.findall(path.read_text(encoding="utf-8"))
        for path in SHELL_FILES
    }
    assert not {path: hits for path, hits in offenders.items() if hits}
