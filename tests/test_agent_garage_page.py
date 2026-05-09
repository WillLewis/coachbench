from __future__ import annotations

from pathlib import Path


def test_garage_page_redirects_to_unified_shell() -> None:
    html = Path("ui/garage.html").read_text(encoding="utf-8")

    assert "app.html#/garage" in html
    assert 'src="topbar.js"' in html
    assert 'id="garageTierSelector"' not in html


def test_unified_shell_declares_workbench_and_backend_draft_status() -> None:
    html = Path("ui/app.html").read_text(encoding="utf-8")
    left_rail = Path("ui/left_rail.js").read_text(encoding="utf-8")

    assert 'data-route="garage"' in html
    assert 'id="draftSourceStatus"' in html
    assert "/v1/drafts" in left_rail
    assert "Backend source" in left_rail
    assert "Offline mode" in left_rail


def test_replay_detail_uses_compact_agent_card_not_big_garage_panel() -> None:
    html = Path("ui/app.html").read_text(encoding="utf-8")
    script = Path("ui/app.js").read_text(encoding="utf-8")

    assert 'class="panel compact-agent-card"' in html
    assert 'id="agentCard"' in html
    assert 'id="garage"' not in html
    assert "function renderCompactAgentCard" in script
    assert "function profileEditor" not in script
