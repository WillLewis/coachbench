# P0-1 Backend Audit

## What Already Works

- `arena/api/app.py` has a small FastAPI shell with route modules for agents, challenges, jobs, leaderboard, and admin registration.
- `arena/storage/registry.py` owns the local SQLite connection and preserves tier metadata for public policy agents.
- `arena/storage/leaderboard.py` already models seasons and aggregate runs, but it is season-oriented rather than user draft/session-oriented.
- `arena/api/routes_challenges.py`, `routes_jobs.py`, and `arena/worker/main.py` prove the queue and report path for longer async work; those are better promoted in P0-2 than duplicated now.
- `arena/tiers/declarative.py`, `arena/tiers/prompt_policy.py`, `arena/tiers/factory.py`, and `arena/tiers/bridge.py` already validate and adapt declarative/prompt-policy configs into engine agents.
- `CoachBenchEngine.run_drive(...)` already accepts two agents, a seed, and `max_plays`, then returns deterministic replay JSON suitable for local persistence.

## Missing For P0-1

- No persisted user-facing draft model with named/versioned tier configs.
- No session model connecting drafts, seeds, replay paths, and run status.
- No direct local API endpoint to run a fresh drive from two saved drafts.
- No stable replay API URL for a locally persisted run.
- No LLM budget gate, status route, call ledger, concurrency ledger, or documented launch cost env vars.
- No tests covering draft lifecycle, draft validation, drive determinism through the HTTP API, or budget caps.

## Reuse Decisions

- Reuse the existing tier validators and `tiered_agent_from_submission(...)` factory by materializing draft configs into local draft config files at run time.
- Reuse `CoachBenchEngine.run_drive(...)` directly for P0-1 single-drive execution; leave queue-backed best-of-N, gauntlets, and tournaments for P0-2.
- Add draft/session/LLM storage modules that initialize their own SQLite tables through a new migration, instead of expanding the existing registry module into unrelated concerns.
- Add a new synchronous `/v1/runs/drive` route now, with shared `arena/runs/run_drive.py` logic so P0-2 workers can call the same path later.
- Do not wire UI, identities, batch jobs, or a real LLM client in this phase.
