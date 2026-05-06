# Phase 6A Completion Audit

Phase 6A lands the public access pivot for Tier 0-2 while keeping Tier 3 private/admin-only. Tier 1 is deterministic prompt-policy; runtime LLM-driven prompt agents are deferred to Phase 6B.

## Deliverables

| Deliverable | Files | Locking tests |
|---|---|---|
| Canonical tier model doc | `docs/tier_0_2_access_model.md` | Documentation review |
| Tier vocabulary | `arena/tiers/__init__.py` | `tests/arena/test_tier_constants.py` |
| Tier storage and endpoint secret handling | `arena/storage/registry.py` | `tests/arena/test_tier_registry.py` |
| Sanitized observation builder | `arena/tiers/sanitized_observation.py` | `tests/arena/test_observation_sanitization.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Tier bridge and deterministic fallback | `arena/tiers/bridge.py` | `tests/arena/test_tier_bridge.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Tier 0 declarative adapter | `arena/tiers/declarative.py`, `data/agent_configs/tier0_efficiency_optimizer.json`, `data/agent_configs/tier0_pressure_look_defender.json` | `tests/arena/test_tier0_declarative.py` |
| Tier 1 prompt-policy adapter | `arena/tiers/prompt_policy.py`, `data/agent_configs/tier1_constraint_setter.json` | `tests/arena/test_tier1_prompt_policy.py` |
| Tier 2 remote endpoint adapter | `arena/tiers/remote_endpoint.py`, `data/agent_configs/tier2_endpoint_example.json` | `tests/arena/test_tier2_remote_endpoint.py` |
| League eligibility | `arena/tiers/league.py` | `tests/arena/test_league_eligibility.py` |
| Safety badges | `arena/tiers/badges.py` | `tests/arena/test_safety_badges.py` |
| Tier-aware agent/challenge/leaderboard routes | `arena/api/routes_agents.py`, `arena/api/routes_challenges.py`, `arena/api/routes_leaderboard.py` | `tests/arena/test_tier_dispatch.py`, `tests/arena/test_routes_agents.py`, `tests/arena/test_routes_challenges.py` |
| Tier worker dispatch | `arena/worker/main.py`, `arena/tiers/factory.py` | `tests/arena/test_tier_dispatch.py` |
| Contract validators | `engine/coachbench/contracts.py` | `tests/arena/test_tier2_remote_endpoint.py`, `tests/arena/test_tier_dispatch.py` |

## Tier 0-2 Invariants

| Invariant | Locking tests |
|---|---|
| Legal-action only | `tests/arena/test_tier_bridge.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Hidden-state safety | `tests/arena/test_observation_sanitization.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Raw-seed safety | `tests/arena/test_routes_leaderboard.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Illegal-action rejection before resolve | `tests/arena/test_phase6a_invariants_intact.py` |
| Remote endpoints cannot mutate engine state | `tests/arena/test_phase6a_invariants_intact.py` |
| Slow/failing agents fall back | `tests/arena/test_tier2_remote_endpoint.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Tier 0/1 replay determinism | `tests/arena/test_tier0_declarative.py`, `tests/arena/test_tier1_prompt_policy.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Public API leak prevention | `tests/arena/test_tier_dispatch.py`, `tests/arena/test_phase6a_invariants_intact.py` |

## Scope Statement

Tier 2 is local-mode only and not production-ready until the gaps in `docs/hosted_arena_design.md` close. Tier 1 runtime LLM execution is Phase 6B, not Phase 6A.

