from __future__ import annotations

from arena.storage.registry import connect
from arena.worker.main import process_one
from arena.worker.queue import enqueue, get_job


def test_worker_process_one_marks_job_done(tmp_path) -> None:
    db_path = tmp_path / "arena.sqlite3"
    conn = connect(db_path)
    source_path = tmp_path / "agent.py"
    source_path.write_text("from agents.example_agent import ExampleCustomOffense\n", encoding="utf-8")
    conn.execute(
        """
        INSERT INTO agent_submissions
        (agent_id, owner_id, name, version, source_hash, source_path, side, submitted_at,
         qualification_status, label, access_tier)
        VALUES ('agent', 'owner', 'agent', 'v1', 'hash', ?, 'offense', 'now',
                'pending', 'Agent', 'sandboxed_code')
        """,
        (str(source_path),),
    )
    conn.commit()
    job_id = enqueue(
        conn,
        "qualification",
        {
            "agent_id": "agent",
            "source_path": str(source_path),
            "agent_path": "agents.example_agent.ExampleCustomOffense",
            "side": "offense",
        },
    )
    assert process_one(db_path)
    assert get_job(conn, job_id)["status"] == "done"
