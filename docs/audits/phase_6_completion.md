# Phase 6 PR 1 Completion Audit

PR 1 lands the local-mode Tier 3 foundation for uploaded-code agents. Tier 0-2 public access lands in PR 2.

- Team config: `engine/coachbench/team_config.py`; `tests/test_team_config.py`.
- Agent validator: `scripts/validate_agent.py`; `tests/test_run_validate_agent.py`.
- Gauntlet: `scripts/run_gauntlet.py`; `tests/test_run_gauntlet.py`.
- Best-of-N: `scripts/run_best_of_n.py`; `tests/test_run_best_of_n.py`.
- Static validation: `arena/sandbox/static_validation.py`; `tests/arena/test_static_validation.py`.
- Qualification: `arena/sandbox/qualification.py`; `tests/arena/test_qualification.py`.
- Sandbox runner: `arena/sandbox/runner.py`; `tests/arena/test_sandbox_runner.py`.
- Tier-aware registry: `arena/storage/registry.py`; `tests/arena/test_registry.py`, `tests/arena/test_registry_tiers.py`.
- Agent routes: `arena/api/routes_agents.py`; `tests/arena/test_routes_agents.py`.
- Challenge routes: `arena/api/routes_challenges.py`; `tests/arena/test_routes_challenges.py`.
- Leaderboard routes/storage: `arena/api/routes_leaderboard.py`, `arena/storage/leaderboard.py`; `tests/arena/test_leaderboard.py`.
- Job polling/worker: `arena/api/routes_jobs.py`, `arena/worker/queue.py`, `arena/worker/main.py`; `tests/arena/test_worker.py`.
- Admin moderation: `arena/admin/routes.py`; `tests/arena/test_admin.py`.

Invariant locks:

- Tier 3 endpoints require admin token.
- Public leaderboard reads exclude `sandboxed_code` rows.
- Raw seeds are stored only in mode-0600 local secrets files.
- User-uploaded code flows through static validation, qualification, and sandbox execution.
