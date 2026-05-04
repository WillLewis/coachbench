from __future__ import annotations

from arena.storage.registry import connect
from arena.worker.main import process_one
from arena.worker.queue import enqueue, get_job


def test_worker_process_one_marks_job_done(tmp_path) -> None:
    db_path = tmp_path / "arena.sqlite3"
    conn = connect(db_path)
    job_id = enqueue(conn, "qualification", {"agent_id": "agent"})
    assert process_one(db_path)
    assert get_job(conn, job_id)["status"] == "done"
