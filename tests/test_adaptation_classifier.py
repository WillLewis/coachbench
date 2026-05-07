from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from coachbench.adaptation import classify_adaptation_reasons


FIXTURES = sorted(Path("tests/fixtures/adaptation").glob("*.json"))


@pytest.mark.parametrize("fixture_path", FIXTURES, ids=lambda path: path.stem)
def test_python_adaptation_classifier_fixtures(fixture_path: Path) -> None:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert classify_adaptation_reasons(fixture["plays"], fixture["graph_cards"]) == {
        int(index): reason for index, reason in fixture["expected"].items()
    }


@pytest.mark.skipif(shutil.which("node") is None, reason="node is unavailable")
@pytest.mark.parametrize("fixture_path", FIXTURES, ids=lambda path: path.stem)
def test_js_classifier_matches_python_source_of_truth(fixture_path: Path) -> None:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    expected = classify_adaptation_reasons(fixture["plays"], fixture["graph_cards"])
    script = f"""
      globalThis.window = globalThis;
      require('./ui/adaptation.js');
      const fixture = {json.dumps(fixture)};
      const actual = window.CBAdaptation.classifyAdaptationReasons(fixture.plays, fixture.graph_cards);
      console.log(JSON.stringify(actual));
    """

    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        text=True,
        capture_output=True,
        timeout=10,
    )

    actual = {int(index): reason for index, reason in json.loads(completed.stdout).items()}
    assert actual == expected
