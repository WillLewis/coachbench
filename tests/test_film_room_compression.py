from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path


def _render_film_room(replay: dict) -> str:
    app_source = Path("ui/app.js").read_text(encoding="utf-8").split("CBRouter.subscribe")[0]
    graph = json.loads(Path("graph/redzone_v0/interactions.json").read_text(encoding="utf-8"))
    concepts = json.loads(Path("graph/redzone_v0/concepts.json").read_text(encoding="utf-8"))
    labels = {
        item["id"]: item.get("label") or item.get("name")
        for item in [*concepts.get("offense", []), *concepts.get("defense", [])]
    }
    graph_cards = {card["id"]: card for card in graph["interactions"]}
    script = f"""
const vm = require('node:vm');
const context = {{
  console,
  matchMedia: () => ({{ matches: false }}),
  replayPayload: {json.dumps(replay)},
  graphCardsPayload: {json.dumps(graph_cards)},
  conceptLabelsPayload: {json.dumps(labels)},
}};
vm.runInNewContext({json.dumps(app_source)} + `
runtime.graphCards = graphCardsPayload;
runtime.conceptLabels = conceptLabelsPayload;
globalThis.outputHtml = renderFilmRoomHtml(replayPayload);
`, context);
process.stdout.write(context.outputHtml);
"""
    result = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout


def test_compressed_film_room_renders_four_headers_for_demo_replay() -> None:
    replay = json.loads(Path("ui/demo_replay.json").read_text(encoding="utf-8"))
    html = _render_film_room(replay)

    for header in ("Turning Point", "Why It Mattered", "Next Try", "Evidence"):
        assert header in html
    assert "<li title=" in html
    assert "Recommendation derived from sequencing" not in html
    assert "View full notes" in html


def test_compressed_film_room_shows_sequencing_fallback_only_when_warranted() -> None:
    replay = json.loads(Path("ui/demo_replay.json").read_text(encoding="utf-8"))
    fallback_replay = copy.deepcopy(replay)
    fallback_replay["film_room"]["next_adjustment"] = "Next try: Outside Zone to counter sequencing."

    html = _render_film_room(fallback_replay)

    assert "Recommendation derived from sequencing" in html
    assert "Play-action gains value after credible run tendency" in html


def test_compressed_film_room_requires_engine_next_try_source() -> None:
    replay = json.loads(Path("ui/demo_replay.json").read_text(encoding="utf-8"))
    missing_next = copy.deepcopy(replay)
    missing_next["film_room"].pop("next_try", None)
    missing_next["film_room"].pop("next_adjustment", None)

    html = _render_film_room(missing_next)

    assert "No turning point this drive." in html
