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

## Phase 6A PR 2 Core Public Access Pivot

PR 2 adds public Tier 0-2 adapters while keeping Tier 3 private/admin-only. Full docs and hardening remain PR 3 scope.

- Tier vocabulary: `arena/tiers/__init__.py`; `tests/arena/test_tier_constants.py`.
- Tier storage and endpoint secrets: `arena/storage/registry.py`; `tests/arena/test_tier_registry.py`.
- Sanitized observation bridge: `arena/tiers/base.py`, `arena/tiers/bridge.py`, `arena/tiers/sanitized_observation.py`; `tests/arena/test_tier_bridge.py`, `tests/arena/test_observation_sanitization.py`.
- Tier 0 declarative adapter: `arena/tiers/declarative.py`, `data/agent_configs/tier0_efficiency_optimizer.json`; `tests/arena/test_tier0_declarative.py`.
- Tier 1 deterministic prompt-policy adapter: `arena/tiers/prompt_policy.py`, `data/agent_configs/tier1_constraint_setter.json`; `tests/arena/test_tier1_prompt_policy.py`.
- Tier 2 remote endpoint adapter: `arena/tiers/remote_endpoint.py`, `data/agent_configs/tier2_endpoint_example.json`; `tests/arena/test_tier2_remote_endpoint.py`.
- League eligibility and safety badges: `arena/tiers/league.py`, `arena/tiers/badges.py`; `tests/arena/test_league_eligibility.py`, `tests/arena/test_safety_badges.py`.
- Tier-aware API dispatch: `arena/api/routes_agents.py`, `arena/api/routes_challenges.py`, `arena/api/routes_leaderboard.py`; `tests/arena/test_tier_dispatch.py`.
