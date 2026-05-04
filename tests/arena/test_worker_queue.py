from __future__ import annotations

from arena.storage.registry import connect
from arena.worker.queue import claim_next, enqueue, finish, get_job


def test_queue_status_transitions() -> None:
    conn = connect(":memory:")
    job_id = enqueue(conn, "qualification", {"agent_id": "a"})
    assert get_job(conn, job_id)["status"] == "pending"
    claimed = claim_next(conn)
    assert claimed["job_id"] == job_id
    finish(conn, job_id, "done")
    assert get_job(conn, job_id)["status"] == "done"
