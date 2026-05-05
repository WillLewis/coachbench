from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.deps import ADMIN_TOKEN
from arena.api.app import app, db
from arena.worker.queue import enqueue


def test_job_status_route_is_admin_gated(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    job_id = enqueue(db(), "qualification", {"agent_id": "a"})
    client = TestClient(app)
    assert client.get(f"/v1/jobs/{job_id}").status_code == 403
    response = client.get(f"/v1/jobs/{job_id}", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
