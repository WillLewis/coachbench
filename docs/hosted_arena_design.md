# Hosted Arena Design Notes

CoachBench Phase 6 and 6A are local-mode arena foundations. They do not authorize public cloud hosting. Product tier semantics are in [Tier 0-2 Access Model](tier_0_2_access_model.md), security invariants are in [Security Notes](security.md), and local operation is in [Arena README](../arena/README.md).

## Trust Boundaries

```text
User config / prompt / endpoint metadata
  -> Arena API validation
  -> Tier adapter or sandbox worker
  -> CoachBench engine public protocol
  -> Replay / reports / leaderboard

Admin token
  -> Admin-only moderation and Tier 3 controls

Hidden seeds and endpoint secrets
  -> mode-0600 local secret files
  -> hashes in public-facing records

Uploaded Tier 3 source
  -> static validation
  -> subprocess sandbox
  -> qualification / private challenge
```

Trust boundaries:

- Tier 0 and Tier 1 inputs are untrusted configuration, not code.
- Tier 2 endpoints are untrusted remote decision services.
- Tier 3 uploaded source is untrusted code and remains local/private/admin-only.
- The engine, graph, legal-action enumerator, observation builders, and replay validators remain trusted.
- Public API responses are untrusted-display surfaces and must omit admin-only and secret fields.

## Phase 6 Tier 3 Sandbox Architecture

Phase 6 reframes uploaded-code execution as the Tier 3 foundation, not the public access path.

Local-mode flow:

```text
Upload .py source
  -> AST static validation
  -> registry row with access_tier=sandboxed_code
  -> qualification job
  -> sandboxed subprocess drive
  -> replay validation
  -> admin/private challenge or sandbox leaderboard
```

Current local controls:

- AST validation denies network, subprocess, dynamic import, file access, threading, process, and unsafe reflection patterns.
- Subprocess execution uses isolated Python flags.
- Worker environment is stripped.
- POSIX resource limits cap memory, CPU, file descriptors, and process count where supported.
- Each run uses an ephemeral cwd.
- Raw seeds are stored outside public responses and represented by hashes.
- Admin routes require `X-Admin-Token`.

Local-mode limits:

- This is not a kernel security boundary.
- It does not defend against all same-user host compromise risks.
- It does not provide production network isolation.
- It does not provide KMS-backed secret storage.

## Phase 6A Tier 0-2 Architecture

Phase 6A adds the public access path without executing uploaded code.

Tier flow:

```text
Tier 0 config / Tier 1 deterministic policy / Tier 2 HTTPS endpoint
  -> tier-specific validation
  -> sanitized observation bridge
  -> adapter decision
  -> deterministic fallback on invalid / slow / failed decision
  -> legal action builder
  -> engine validation before resolution
  -> replay and leaderboard
```

Key components:

- `arena/tiers/sanitized_observation.py` removes hidden fields, raw seeds, legal action set identifiers, and resource snapshot internals.
- `arena/tiers/bridge.py` converts adapter decisions into legal engine actions and falls back deterministically on failures.
- `arena/tiers/declarative.py` implements Tier 0.
- `arena/tiers/prompt_policy.py` implements Tier 1 as deterministic rules. LLM-driven prompts are deferred to Phase 6B.
- `arena/tiers/remote_endpoint.py` implements Tier 2 request/response validation and local-mode network controls.
- `arena/tiers/league.py` separates rookie, policy, endpoint, sandbox, and research leagues.
- `arena/tiers/badges.py` derives public safety badges.

## Production Gap List

Before any cloud deploy, close these gaps:

- Real container isolation such as gVisor, Firecracker, or equivalent.
- Network policy at the runtime layer.
- mTLS between API and worker.
- KMS-backed seed and endpoint secret storage.
- Immutable audit logs.
- Abuse handling pipeline.
- DMCA and takedown flow.
- Terms of Service and content policy.
- Content moderation human-in-the-loop.
- Edge rate limiting.
- Signed challenge handshake for Tier 2.
- DNS rebinding protection.
- Registered endpoint allowlist.
- Replay-attack defense.

Phase 6 is the Tier 3 local/private/admin foundation. Phase 6A is the public Tier 0-2 access pivot. Neither is a production-hosting approval.

