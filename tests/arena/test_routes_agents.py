from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.deps import ADMIN_TOKEN
from arena.api.app import app


def _upload(client: TestClient, token: str | None = ADMIN_TOKEN, name: str = "local_agent", filename: str = "agent.py", data: bytes | None = None):
    headers = {"X-Admin-Token": token} if token else {}
    files = {"file": (filename, data or b"from agents.example_agent import ExampleCustomOffense\n", "text/x-python")}
    form = {"name": name, "version": "v1", "label": "Local Agent", "side": "offense", "owner_id": "owner"}
    return client.post("/v1/agents", data=form, files=files, headers=headers)


def test_multipart_upload_admin_happy_path(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    response = _upload(client)
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "pending"
    assert response.json()["job_id"]


def test_upload_requires_admin_token(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    response = _upload(TestClient(app), token=None)
    assert response.status_code == 403


def test_upload_rejects_non_py_and_large_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    assert _upload(client, filename="agent.txt").status_code == 422
    assert _upload(client, data=b"x" * (65 * 1024)).status_code == 422


def test_upload_rejects_banned_name(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    response = _upload(TestClient(app), name="nfl_agent")
    assert response.status_code == 422
