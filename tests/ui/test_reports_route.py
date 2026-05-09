from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_reports_route_has_recent_report_mounts_and_match_affordances() -> None:
    html = (ROOT / "ui/app.html").read_text(encoding="utf-8")
    js = (ROOT / "ui/app.js").read_text(encoding="utf-8")

    assert "Recent Arena Reports" in html
    assert 'id="reportsList"' in html
    assert 'id="reportDetail"' in html

    assert "/v1/arena/reports?limit=20" in js
    assert "/v1/arena/jobs/${encodeURIComponent(jobId)}/report" in js
    assert "data-open-replay" in js
    assert "data-discuss-film" in js
    assert "Watch Film" in js
    assert "Discuss with Assistant" in js
    assert "type: 'film_room_tweak'" in js
