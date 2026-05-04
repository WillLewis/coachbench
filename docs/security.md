# Security Notes

Hosted third-party execution is out of scope for the starter repo.

Minimum future posture for hosted execution:

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

Do not implement hosted uploads or arbitrary code execution without a sandbox design review.

## Phase 6 Local-Mode Additions

Phase 6 adds local-only arena primitives:

```text
AST static validation
isolated subprocess runner
stripped worker environment
ephemeral working directories
CPU / memory / file descriptor limits where supported
SQLite registry and queue
admin-token-gated moderation endpoints
hidden-seed leaderboard hashes
```

Remaining gaps before public hosting:

```text
real container isolation
network policy outside Python
KMS-backed seed storage
immutable audit logs
rate limiting
abuse handling
human moderation
legal review
```
