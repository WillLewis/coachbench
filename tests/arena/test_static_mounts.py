from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app


def test_fastapi_serves_ui_and_static_data_from_same_origin() -> None:
    client = TestClient(app)

    app_html = client.get("/ui/app.html")
    assert app_html.status_code == 200
    assert "CoachBench Workbench" in app_html.text

    graph = client.get("/graph/redzone_v0/interactions.json")
    assert graph.status_code == 200
    assert "interactions" in graph.json()

    glossary = client.get("/agent_garage/parameter_glossary.json")
    assert glossary.status_code == 200
    assert "risk_tolerance" in glossary.json()

    replay = client.get("/data/demo_replay.json")
    assert replay.status_code == 200
    assert "plays" in replay.json()
