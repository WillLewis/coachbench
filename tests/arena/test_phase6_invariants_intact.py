from __future__ import annotations

import os

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app, db
from arena.api.deps import ADMIN_TOKEN
from arena.sandbox.runner import run_in_sandbox
from arena.sandbox.static_validation import FORBIDDEN_IMPORT_NAMES, validate_agent_source
from arena.storage.leaderboard import add_run
from arena.storage.registry import register_submission


def test_sandbox_runner_still_enforces_timeout_and_memory_caps(tmp_path) -> None:
    loop = tmp_path / "loop.py"
    loop.write_text("while True:\n    pass\n", encoding="utf-8")
    timeout = run_in_sandbox(loop, [], cwd=tmp_path, timeout_seconds=0.2, memory_bytes=128 * 1024 * 1024)
    assert not timeout.ok
    assert timeout.reason == "timeout"

    if os.name != "posix":
        pytest.skip("POSIX resource limits unavailable")
    oom = tmp_path / "oom.py"
    oom.write_text("x = bytearray(512 * 1024 * 1024)\n", encoding="utf-8")
    result = run_in_sandbox(oom, [], cwd=tmp_path, timeout_seconds=2.0, memory_bytes=64 * 1024 * 1024)
    if result.ok:
        pytest.skip("RLIMIT_AS not enforced by this local platform")
    assert result.reason in {"oom", "exit_nonzero"}


def test_static_validator_rejects_every_forbidden_import_name() -> None:
    for name in sorted(FORBIDDEN_IMPORT_NAMES):
        issues = validate_agent_source(f"import {name}\n")
        assert any(issue.code == "E_FORBIDDEN_IMPORT" for issue in issues), name


def test_registry_rejects_sandboxed_code_from_non_admin(tmp_path) -> None:
    source = tmp_path / "agent.py"
    source.write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(PermissionError):
        register_submission(db(), "owner", "code_agent", "v1", source, "offense", "Code Agent")


def test_public_leaderboard_excludes_sandboxed_code_rows(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    season = client.post(
        "/v1/admin/seasons",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        json={"label": "Sandbox", "seeds": [42], "max_plays": 8, "opponent_kind": "static"},
    ).json()["season_id"]
    add_run(db(), season, "tier3", 42, 7, "touchdown", 4, "sandboxed_code")
    public = client.get(f"/v1/seasons/{season}/leaderboard")
    assert public.status_code == 200
    assert public.json()["standings"] == []
    assert "42" not in public.text


def test_sample_admin_routes_require_admin_token(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    for method, path, kwargs in (
        ("get", "/v1/admin/agents", {}),
        ("get", "/v1/admin/jobs", {}),
        ("post", "/v1/admin/seasons", {"json": {"label": "Local", "seeds": [42], "max_plays": 8, "opponent_kind": "static"}}),
    ):
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 403
