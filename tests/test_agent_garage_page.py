from __future__ import annotations

import re
from pathlib import Path


def test_garage_route_declares_tier_selector_controls_and_rule_builder() -> None:
    html = Path("ui/garage.html").read_text(encoding="utf-8")
    script = Path("ui/app.js").read_text(encoding="utf-8")

    assert 'data-route="garage"' in html
    assert 'id="garageTierSelector"' in html
    assert re.findall(r'name="garage_tier" value="([^"]+)"', html) == [
        "declarative",
        "prompt_policy",
        "remote_endpoint",
    ]
    assert "Tier 0" in html
    assert "Tier 1" in html
    assert "Tier 2" in html

    assert 'data-control-section="identity"' in html
    assert 'data-control-section="strategy"' in html
    assert 'data-control-section="resource"' not in html
    assert 'data-rule-builder' in html
    assert 'id="ruleChain"' in html
    assert "CBEmptyStates.emptyAgents()" in script


def test_replay_detail_uses_compact_agent_card_not_big_garage_panel() -> None:
    html = Path("ui/replay.html").read_text(encoding="utf-8")
    script = Path("ui/app.js").read_text(encoding="utf-8")

    assert 'class="panel compact-agent-card"' in html
    assert 'id="agentCard"' in html
    assert 'id="garage"' not in html
    assert "function renderCompactAgentCard" in script
    assert "function profileEditor" not in script
