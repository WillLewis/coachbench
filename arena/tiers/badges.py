from __future__ import annotations


def derive_badges(submission: dict) -> list[str]:
    tier = submission.get("access_tier")
    badges = ["hidden_state_safe"]
    if tier == "declarative":
        badges.extend(["config_agent", "network_off"])
    elif tier == "prompt_policy":
        badges.extend(["prompt_agent", "network_off"])
    elif tier == "remote_endpoint":
        badges.append("remote_agent")
    elif tier == "sandboxed_code":
        badges.extend(["sandboxed_agent", "network_off"])
    if submission.get("qualification_status") == "passed":
        badges.append("verified_replayable")
    return badges
