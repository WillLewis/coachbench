from __future__ import annotations

ACCESS_TIERS = ("declarative", "prompt_policy", "remote_endpoint", "sandboxed_code")

TIER_LABELS = {
    "declarative": "Tier 0 - Declarative config",
    "prompt_policy": "Tier 1 - Prompt-policy (deterministic)",
    "remote_endpoint": "Tier 2 - Remote endpoint",
    "sandboxed_code": "Tier 3 - Uploaded code (admin)",
}

PUBLIC_TIERS = {"declarative", "prompt_policy", "remote_endpoint"}
ADMIN_ONLY_TIERS = {"sandboxed_code"}
