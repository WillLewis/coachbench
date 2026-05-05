# CoachBench Arena Local Mode

**LOCAL MODE ONLY.** Bind to `127.0.0.1` for development. Do not expose this service publicly; production hosting requires a separate threat model.

## Install And Run

```bash
pip install -e ".[arena]"
uvicorn arena.api.app:app --host 127.0.0.1 --port 8765
python -m arena.worker
```

Set `COACHBENCH_ADMIN_TOKEN` before startup. If absent, local mode prints a random token to stderr.

Phase 6 lands the Tier 3 uploaded-code foundation. Every PR 1 upload is registered as `access_tier="sandboxed_code"` and is admin-only. Tier 0-2 public access lands in PR 2.
