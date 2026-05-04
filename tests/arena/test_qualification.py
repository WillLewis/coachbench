from __future__ import annotations

from pathlib import Path

from arena.sandbox.qualification import qualify_agent_source


def test_example_custom_agent_qualifies() -> None:
    report = qualify_agent_source(
        source=Path("agents/example_agent.py").read_text(encoding="utf-8"),
        agent_path="agents.example_agent.ExampleCustomOffense",
        side="offense",
        opponent_path="agents.static_defense.StaticDefense",
        seeds=[42],
        max_plays=1,
    )
    assert report["passed"], report


def test_fallback_agent_fails_qualification() -> None:
    source = Path("tests/fixtures/phase3_agents.py").read_text(encoding="utf-8")
    report = qualify_agent_source(
        source=source,
        agent_path="tests.fixtures.phase3_agents.IllegalConceptOffense",
        side="offense",
        opponent_path="agents.static_defense.StaticDefense",
        seeds=[42],
        max_plays=1,
    )
    assert not report["passed"]
    assert "V2" in report["reasons"]
