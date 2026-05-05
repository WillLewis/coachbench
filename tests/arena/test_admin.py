from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app
from arena.api.deps import ADMIN_TOKEN


def test_admin_endpoints_require_token(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    response = client.get("/v1/admin/agents")
    assert response.status_code == 403
    response = client.get("/v1/admin/agents", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert response.status_code == 200
