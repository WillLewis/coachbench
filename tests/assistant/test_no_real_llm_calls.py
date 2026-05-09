from __future__ import annotations

from pathlib import Path


FORBIDDEN = ("anthropic", "openai", "httpx", "requests", "call_llm_stub")


def test_assistant_package_does_not_import_real_or_p0_1_llm_clients() -> None:
    offenders: dict[str, list[str]] = {}
    for path in Path("arena/assistant").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        hits = [token for token in FORBIDDEN if token in text]
        if hits:
            offenders[str(path)] = hits
    assert offenders == {}
