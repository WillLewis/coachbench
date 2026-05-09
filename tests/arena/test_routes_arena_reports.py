from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app, db
from arena.storage import arena_jobs
from arena.worker.queue import enqueue, finish


def test_arena_reports_lists_completed_report_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    conn = db()
    job_id = enqueue(conn, "arena_best_of_n", {"n": 1})
    arena_jobs.create_progress(conn, job_id, 1)
    arena_jobs.increment_progress(conn, job_id)
    report_path = Path("arena/storage/local/arena_reports") / f"{job_id}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text('{"job_id":"' + job_id + '","matches":[]}', encoding="utf-8")
    arena_jobs.attach_report(conn, job_id, str(report_path))
    finish(conn, job_id, "completed")

    response = TestClient(app).get("/v1/arena/reports?limit=5")

    assert response.status_code == 200, response.text
    reports = response.json()["reports"]
    assert len(reports) == 1
    assert reports[0]["job_id"] == job_id
    assert reports[0]["kind"] == "best_of_n"
    assert reports[0]["status"] == "completed"
    assert reports[0]["completed_runs"] == 1
    assert reports[0]["total_runs"] == 1
    assert reports[0]["has_report"] is True
