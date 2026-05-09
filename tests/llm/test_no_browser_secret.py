from __future__ import annotations

from pathlib import Path
import re


def test_ui_assets_do_not_reference_model_secret_paths() -> None:
    pattern = re.compile(r"OPENAI|ANTHROPIC|api_key|sk-")
    offenders: list[str] = []
    for path in Path("ui").rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if pattern.search(text):
            offenders.append(str(path))
    assert offenders == []
