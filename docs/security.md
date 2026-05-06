# CoachBench Security Notes

CoachBench arena work is local-mode only. Public cloud hosting requires the gap closures listed in [Hosted Arena Design](hosted_arena_design.md). Product semantics for public Tier 0-2 access are in [Tier 0-2 Access Model](tier_0_2_access_model.md), with local run guidance in [Arena README](../arena/README.md).

## A. Phase 6 Tier 3 Invariants

Tier 3 — Uploaded-code agent (local/private/admin-only) executes untrusted Python only through the local sandbox path.

| Invariant | Current lock |
|---|---|
| Local mode binds to `127.0.0.1` and rejects public bind addresses. | `arena/api/server.py`; `tests/arena/test_local_bind.py` |
| Uploaded source goes through AST validation before execution. | `arena/sandbox/static_validation.py`; `tests/arena/test_static_validation.py`, `tests/arena/test_phase6_invariants_intact.py` |
| Sandbox runner uses isolated Python, stripped environment, ephemeral cwd, timeouts, and POSIX limits where available. | `arena/sandbox/runner.py`; `tests/arena/test_sandbox_runner.py`, `tests/arena/test_phase6_invariants_intact.py` |
| Qualification composes static validation and sandboxed drive execution. | `arena/sandbox/qualification.py`; `tests/arena/test_qualification.py` |
| Tier 3 endpoints and admin routes require `X-Admin-Token`. | `arena/api/routes_agents.py`, `arena/api/routes_challenges.py`, `arena/admin/routes.py`; `tests/arena/test_admin_gate.py`, `tests/arena/test_phase6_invariants_intact.py` |
| Tier 3 entries are excluded from public leaderboards. | `arena/api/routes_leaderboard.py`, `arena/storage/leaderboard.py`; `tests/arena/test_routes_leaderboard.py`, `tests/arena/test_phase6_invariants_intact.py` |
| Raw seeds are stored only in mode-0600 local secrets files and public responses use hashes. | `arena/storage/leaderboard.py`; `tests/arena/test_leaderboard.py` |
| Registry stores `access_tier` with the four canonical values. | `arena/storage/registry.py`; `tests/arena/test_registry_tiers.py` |

Minimum future posture from the starter security note remains in force:

```text
no network by default
non-root runner
read-only filesystem
CPU/memory/PID limits
per-action timeout
per-match timeout
hidden seeds never passed to agents
agents receive observations only
ephemeral workspaces
separate worker pool from API/UI
no shared secrets in runner environment
logs scrubbed before display
dependency allowlist at first
```

## B. Phase 6A Tier 0-2 Invariants

Tier 0 — Declarative config agent, Tier 1 — Prompt-policy agent (deterministic; LLM deferred to Phase 6B), and Tier 2 — Remote endpoint agent are the public access path. They do not execute uploaded code in the CoachBench process.

| Invariant | Current lock |
|---|---|
| Agents only choose among legal actions. | `arena/tiers/bridge.py`; `tests/arena/test_tier_bridge.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Hidden-state safety: tier observations are strict sanitized subsets and exclude `HIDDEN_OBSERVATION_FIELDS`. | `arena/tiers/sanitized_observation.py`; `tests/arena/test_observation_sanitization.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Raw-seed safety: non-admin leaderboard and run responses expose no raw seeds. | `arena/api/routes_leaderboard.py`; `tests/arena/test_routes_leaderboard.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Illegal actions are rejected before resolution by falling back in the tier bridge. | `arena/tiers/bridge.py`; `tests/arena/test_tier_bridge.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Remote endpoints cannot mutate engine state; the endpoint response is only an action candidate. | `arena/tiers/remote_endpoint.py`, `arena/tiers/bridge.py`; `tests/arena/test_tier2_remote_endpoint.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Slow or failing Tier 2 endpoints and Tier 1 decisions fall back deterministically. | `arena/tiers/remote_endpoint.py`, `arena/tiers/bridge.py`; `tests/arena/test_tier2_remote_endpoint.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Replay determinism: Tier 0 and Tier 1 are deterministic functions of config, observation, and memory. Tier 2 is deterministic only if the user's endpoint is deterministic. | `arena/tiers/declarative.py`, `arena/tiers/prompt_policy.py`, `arena/worker/main.py`; `tests/arena/test_tier0_declarative.py`, `tests/arena/test_tier1_prompt_policy.py`, `tests/arena/test_phase6a_invariants_intact.py` |
| Public API leak prevention: public cards omit endpoint URLs, API keys, qualification reports, ban reasons, source paths, and raw seeds. | `arena/api/deps.py`, `arena/api/routes_agents.py`; `tests/arena/test_tier_dispatch.py`, `tests/arena/test_phase6a_invariants_intact.py` |

## C. Tier 2 Secret Storage

Current posture:

- Raw Tier 2 endpoint URLs and optional API keys are stored in mode-0600 JSON files under `arena/storage/secrets/endpoints/`.
- `agent_submissions` stores only `endpoint_url_hash`, not the raw URL or key.
- Public agent cards omit `endpoint_url_hash` and all secret fields.

Production gap:

- Local mode does not provide KMS-backed secret storage. Production would need KMS-backed encryption, key rotation, access auditing, and recovery procedures before Tier 2 is represented as production-ready.

## D. Tier 2 Outbound Network Policy

Current local-mode controls:

- HTTPS-only endpoint registration.
- Redirects disabled.
- Proxy use disabled by client configuration and stripped environment in sandbox paths.
- Denylist for localhost, metadata addresses, private IPv4 CIDRs, and local IPv6 ranges.
- Per-call timeout defaults to 800ms and caps at 2000ms.
- Response size cap is 8 KiB.
- Local in-memory rate limit defaults to 60 calls per minute per agent.

Production gaps:

- Registered endpoint allowlist per agent.
- DNS rebinding protection.
- Controlled egress proxy or firewall.
- Signed challenge handshake.
- Replay-attack protection.
- mTLS for higher-trust tiers.
- Edge rate limiting and abuse response.

Tier 2 must not be represented as production-ready until those controls are implemented.

## E. Tier 3 Remains Local/Private/Admin-Only

Phase 6 is the Tier 3 foundation for uploaded-code agents. It is useful for local development, private evaluation, and admin-gated research. It is not the public access path. Public access is Tier 0-2 only.

## F. Phase 6B Deferred Work

Runtime LLM-driven prompt agents are out of scope for Phase 6A. Phase 6B may introduce them only with additional safety controls:

- rate limits
- cost caps
- model-output schema validation
- fallback to deterministic policy on model failure
- prompt observation sanitization
- no hidden-field or raw-seed exposure to prompts

