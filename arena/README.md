# CoachBench Arena Local Mode

**LOCAL MODE ONLY.** The arena binds to `127.0.0.1` for local development. Production hosting, public ingress, and cloud deployment require a separate threat model and are out of scope.

## Run Locally

```bash
pip install -e ".[arena]"
uvicorn arena.api.app:app --host 127.0.0.1 --port 8765
python -m arena.worker
```

Do not bind to `0.0.0.0`. Local mode stores SQLite state and artifacts under `arena/storage/local/`.

## Agent Flow

1. Upload a single Python module.
2. Static validation checks imports and dynamic access patterns.
3. Qualification runs the agent in the subprocess sandbox.
4. Passed agents can run local challenges and leaderboard seasons.

## Supported Agent Surface

Agents should follow the existing `name` plus `choose_action(observation, memory, legal)` protocol. They receive engine observations only through the existing observation builders and the restricted `LegalActionFacade`.

## Common Rejections

- Network or subprocess imports.
- File access with `open`.
- Dynamic `getattr(obj, name)`.
- `eval`, `exec`, `compile`, or dunder attribute traversal.
- Actions that trigger validator fallback.

## Isolation Posture

Local mode uses AST denial, isolated Python subprocesses, stripped environments, ephemeral working directories, timeouts, and POSIX resource limits where the host honors them. Some local platforms degrade gracefully when a resource limit is unavailable.
