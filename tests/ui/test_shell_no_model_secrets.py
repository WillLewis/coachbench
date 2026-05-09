from __future__ import annotations

import re
from pathlib import Path


SECRET_PATTERN = re.compile(r"OPENAI|ANTHROPIC|api_key|sk-")


def test_ui_contains_no_model_secret_paths() -> None:
    offenders = []
    for path in Path("ui").rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if SECRET_PATTERN.search(text):
                offenders.append(str(path))
    assert offenders == []
