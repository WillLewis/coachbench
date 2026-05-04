# Hosted Arena Design Notes

CoachBench Phase 6 implements local-mode untrusted-code execution only. It does not authorize public hosting.

## Trust Boundaries

- Uploaded agent source is untrusted.
- Arena API state is local SQLite.
- Sandbox subprocesses are disposable and use ephemeral working directories.
- Engine observations remain the only data passed to agents.

## Current Local Isolation

- AST static validation blocks network, subprocess, file, dynamic import, and dynamic attribute patterns.
- Sandbox runner uses `python -I -S`, stripped environment variables, timeouts, and POSIX `resource` limits when available.
- Hidden seeds are represented by hashes outside admin-only local secrets.
- Admin routes require `X-Admin-Token`.

## What Local Mode Does Not Defend Against

- Kernel escape or same-user host compromise.
- Determined side-channel attacks.
- Weak local filesystem permissions outside the project.
- Public internet abuse.

## Required Before Cloud Hosting

- gVisor, Firecracker, or equivalent per-run isolation.
- Network egress policy at the container/runtime layer.
- mTLS between API and worker.
- KMS-backed seed storage.
- Immutable audit logs.
- Rate limiting and abuse handling.
- Human moderation workflow.
- Terms of Service and content policy.
- Incident response and takedown process.
