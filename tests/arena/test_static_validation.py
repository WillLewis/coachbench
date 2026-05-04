from __future__ import annotations

from pathlib import Path

from arena.sandbox.static_validation import validate_agent_source


def _codes(source: str) -> set[str]:
    return {issue.code for issue in validate_agent_source(source)}


def test_static_offense_source_passes_static_validation() -> None:
    assert validate_agent_source(Path("agents/static_offense.py").read_text(encoding="utf-8")) == []


def test_hostile_snippets_hit_expected_error_codes() -> None:
    cases = {
        "import os": "E_FORBIDDEN_IMPORT",
        "eval('1+1')": "E_FORBIDDEN_NAME",
        "getattr(obj, name)": "E_DYNAMIC_GETATTR",
        "open('x', 'w')": "E_FORBIDDEN_NAME",
        "import subprocess": "E_FORBIDDEN_IMPORT",
        "import socket": "E_FORBIDDEN_IMPORT",
        "import threading": "E_FORBIDDEN_IMPORT",
        "import builtins\nbuiltins.eval('1')": "E_FORBIDDEN_IMPORT",
        "x.__class__": "E_DUNDER_ATTRIBUTE",
        "import pickle": "E_FORBIDDEN_IMPORT",
    }
    for source, code in cases.items():
        assert code in _codes(source)


def test_literal_getattr_passes_and_dynamic_getattr_fails() -> None:
    assert validate_agent_source('name = getattr(obj, "name")') == []
    assert "E_DYNAMIC_GETATTR" in _codes("name = getattr(obj, attr)")
