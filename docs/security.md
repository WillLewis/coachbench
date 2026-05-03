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
