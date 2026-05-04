from __future__ import annotations

import json
from pathlib import Path

from arena.storage.registry import connect
from arena.worker.queue import claim_next, finish


def process_one(db_path: Path | str = "arena/storage/local/arena.sqlite3") -> bool:
    conn = connect(db_path)
    job = claim_next(conn)
    if not job:
        return False
    try:
        payload = json.loads(job["payload_json"])
        # Local-mode placeholder: real job kinds are processed by API synchronously until the worker is started.
        if job["kind"] not in {"qualification", "challenge", "leaderboard_run"}:
            raise ValueError(f"unknown job kind: {job['kind']}")
        _ = payload
        finish(conn, job["job_id"], "done")
        return True
    except Exception as exc:
        finish(conn, job["job_id"], "failed", str(exc))
        return False


def main() -> None:
    while process_one():
        pass


if __name__ == "__main__":
    main()
