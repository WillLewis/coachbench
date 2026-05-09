# P0-2 Arena Audit

## Route And Worker Decisions

- `arena/api/routes_challenges.py`: wrap. It is a developer challenge endpoint keyed to registered agents, leagues, and admin-only tiers. Keep it for practitioner flows; add a user-facing draft-based Arena route layer instead.
- `arena/api/routes_jobs.py`: extend behind an Arena alias. The existing `/v1/jobs/{job_id}` is admin-gated and intentionally generic; Arena needs public progress and report URLs without exposing the whole worker queue surface.
- `arena/api/routes_leaderboard.py`: keep developer/admin-only. It models seasons and tier visibility, not saved-draft product sessions.
- `arena/worker/main.py`: promote the dispatch spine. Add Arena job kinds to the existing queue worker instead of building a second runner.
- `arena/worker/queue.py`: extend with sidecar progress metadata rather than mutating the existing jobs schema; existing queue tests and admin routes stay stable.
- `arena/sandbox/runner.py` and `arena/sandbox/qualification.py`: keep developer-only. P0-2 draft Arena runs validated config adapters, not sandboxed user code.

## Script Decisions

- `scripts/run_best_of_n.py`: extend. Keep the current team-file benchmark mode for existing tests/docs, and add draft-backed Arena mode that calls the shared Arena report writer.
- `scripts/run_gauntlet.py`: extend. Keep dotted-agent validation mode; add draft-backed Arena mode for user-facing reports.
- `scripts/run_tournament.py`: extend. Keep team-file round-robin mode; add draft-backed Arena mode for saved drafts.

## Smoke Test Command

```bash
python -m uvicorn arena.api.app:app --host 127.0.0.1 --port 8766
curl -s -X POST http://127.0.0.1:8766/v1/drafts -H 'Content-Type: application/json' --data @/tmp/offense_draft.json
curl -s -X POST http://127.0.0.1:8766/v1/drafts -H 'Content-Type: application/json' --data @/tmp/defense_draft.json
curl -s -X POST http://127.0.0.1:8766/v1/arena/best_of_n -H 'Content-Type: application/json' -d '{"offense_draft_id":"OFFENSE_ID","defense_draft_id":"DEFENSE_ID","n":3,"seed_pack":[42,99,202]}'
python -c 'from arena.worker.main import process_one; process_one()'
curl -s http://127.0.0.1:8766/v1/arena/jobs/JOB_ID
curl -s http://127.0.0.1:8766/v1/arena/jobs/JOB_ID/report
```

## Rationale

The product-facing Arena should be saved-draft first. Existing challenge and leaderboard routes are useful, but they expose registration, tier, and admin vocabulary that would leak implementation detail into the launch UI. The thin Arena route layer can reuse the queue and worker while keeping the user loop focused on drafts, reports, replays, and Film Room links.
