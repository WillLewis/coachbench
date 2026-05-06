# CoachBench Arena Local Mode

**LOCAL MODE ONLY.** Bind to `127.0.0.1`. Do not expose this service publicly; production hosting requires the threat-model gap closures in [Hosted Arena Design](../docs/hosted_arena_design.md).

Product semantics live in [Tier 0-2 Access Model](../docs/tier_0_2_access_model.md). Security invariants live in [Security Notes](../docs/security.md).

## Tier Matrix

| Tier | Label | Public role |
|---|---|---|
| Tier 0 | Declarative config agent | Default public path |
| Tier 1 | Prompt-policy agent (deterministic; LLM deferred to Phase 6B) | Public policy path |
| Tier 2 | Remote endpoint agent | Advanced public path under local-mode controls |
| Tier 3 | Uploaded-code agent (local/private/admin-only) | Private sandbox path |

Tier 2 is not production-ready. Current controls are local-mode controls only; production controls are listed in [Hosted Arena Design](../docs/hosted_arena_design.md).

## League Map

| League | Eligible tiers | Public |
|---|---|---|
| rookie | Tier 0 | Yes |
| policy | Tier 0-1 | Yes |
| endpoint | Tier 0-2 | Yes |
| sandbox | Tier 3 | Admin/private |
| research | Tier 3 | Admin/private |

## Install And Run

```bash
pip install -e ".[arena]"
export COACHBENCH_ADMIN_TOKEN=local-dev-token
uvicorn arena.api.app:app --host 127.0.0.1 --port 8765
python -m arena.worker
```

If `COACHBENCH_ADMIN_TOKEN` is absent, local mode prints a random token to stderr on startup.

## Quick Starts

Tier 0 declarative config:

```bash
curl -s -X POST http://127.0.0.1:8765/v1/agents \
  -F access_tier=declarative \
  -F name=tier0_agent \
  -F version=v1 \
  -F label="Tier 0 Agent" \
  -F side=offense \
  -F owner_id=local \
  -F tier_config=@data/agent_configs/tier0_efficiency_optimizer.json
```

Tier 1 deterministic prompt-policy:

```bash
curl -s -X POST http://127.0.0.1:8765/v1/agents \
  -F access_tier=prompt_policy \
  -F name=tier1_agent \
  -F version=v1 \
  -F label="Tier 1 Agent" \
  -F side=offense \
  -F owner_id=local \
  -F tier_config=@data/agent_configs/tier1_constraint_setter.json
```

Tier 2 remote endpoint:

```bash
curl -s -X POST http://127.0.0.1:8765/v1/agents \
  -F access_tier=remote_endpoint \
  -F name=tier2_agent \
  -F version=v1 \
  -F label="Tier 2 Agent" \
  -F side=offense \
  -F owner_id=local \
  -F endpoint_url=https://example.invalid/agent
```

Tier 3 uploaded code, admin-only:

```bash
curl -s -X POST http://127.0.0.1:8765/v1/agents \
  -H "X-Admin-Token: $COACHBENCH_ADMIN_TOKEN" \
  -F access_tier=sandboxed_code \
  -F name=tier3_agent \
  -F version=v1 \
  -F label="Tier 3 Agent" \
  -F side=offense \
  -F owner_id=local \
  -F source=@agents/example_agent.py
```

Challenge a public agent:

```bash
curl -s -X POST http://127.0.0.1:8765/v1/challenges \
  -H "Content-Type: application/json" \
  -d '{"challenger_agent_id":"AGENT_ID","league":"rookie","opponent_kind":"static","seeds":[42]}'
```

## Troubleshooting

Common Tier 3 static-validation rejections:

- forbidden import such as `socket`, `subprocess`, `os`, or `requests`
- dynamic `getattr`
- `eval`, `exec`, `open`, or dynamic import
- threading or process creation

Common Tier 2 fallback reasons:

- `tier2_timeout`
- `tier2_unreachable`
- `tier2_malformed_response`
- `tier2_invalid_action`
- `tier2_rate_limited`

All tiers still pass through legal-action validation and deterministic fallback before resolution.

