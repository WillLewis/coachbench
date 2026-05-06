# Phase 6 Completion Audit

Phase 6 lands the local/private/admin Tier 3 foundation: Tier 3 — Uploaded-code agent (local/private/admin-only). All uploaded-code agents remain `access_tier="sandboxed_code"` and are excluded from public leagues.

## Deliverables

| Deliverable | Files | Locking tests |
|---|---|---|
| Team config foundation | `engine/coachbench/team_config.py`, `data/teams/*.json` | `tests/test_team_config.py` |
| Agent validator CLI | `scripts/validate_agent.py` | `tests/test_run_validate_agent.py` |
| Local gauntlet | `scripts/run_gauntlet.py` | `tests/test_run_gauntlet.py` |
| Best-of-N runner | `scripts/run_best_of_n.py`, `scripts/_evaluation.py` | `tests/test_run_best_of_n.py` |
| AST static validation | `arena/sandbox/static_validation.py` | `tests/arena/test_static_validation.py`, `tests/arena/test_phase6_invariants_intact.py` |
| Qualification suite | `arena/sandbox/qualification.py` | `tests/arena/test_qualification.py` |
| Sandbox runner | `arena/sandbox/runner.py` | `tests/arena/test_sandbox_runner.py`, `tests/arena/test_phase6_invariants_intact.py` |
| SQLite registry | `arena/storage/registry.py` | `tests/arena/test_registry.py`, `tests/arena/test_registry_tiers.py` |
| Agent routes | `arena/api/routes_agents.py` | `tests/arena/test_routes_agents.py` |
| Challenge routes | `arena/api/routes_challenges.py` | `tests/arena/test_routes_challenges.py` |
| Leaderboard storage/routes | `arena/storage/leaderboard.py`, `arena/api/routes_leaderboard.py` | `tests/arena/test_leaderboard.py`, `tests/arena/test_routes_leaderboard.py` |
| Job queue and worker | `arena/worker/queue.py`, `arena/worker/main.py`, `arena/api/routes_jobs.py` | `tests/arena/test_worker.py`, `tests/arena/test_worker_queue.py`, `tests/arena/test_jobs_route.py` |
| Admin moderation | `arena/admin/routes.py` | `tests/arena/test_admin.py`, `tests/arena/test_admin_gate.py` |
| Local bind protection | `arena/api/server.py` | `tests/arena/test_local_bind.py` |
| Minimal arena README | `arena/README.md` | Documentation review |

## Invariant Locks

- Sandbox runner enforces timeout and resource caps: `tests/arena/test_sandbox_runner.py`, `tests/arena/test_phase6_invariants_intact.py`.
- Static validation rejects forbidden imports and unsafe calls: `tests/arena/test_static_validation.py`, `tests/arena/test_phase6_invariants_intact.py`.
- Non-admin callers cannot register Tier 3: `tests/arena/test_registry_tiers.py`, `tests/arena/test_phase6_invariants_intact.py`.
- Public leaderboard excludes Tier 3 rows: `tests/arena/test_routes_leaderboard.py`, `tests/arena/test_phase6_invariants_intact.py`.
- Admin endpoints require admin token: `tests/arena/test_admin.py`, `tests/arena/test_phase6_invariants_intact.py`.

## Scope Statement

Phase 6 is not public hosted execution. It is the local/private/admin foundation for Tier 3. Public Tier 0-2 access is covered by [Phase 6A Completion Audit](phase_6a_completion.md).

