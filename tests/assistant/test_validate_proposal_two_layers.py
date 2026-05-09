from __future__ import annotations

import copy

import pytest

from arena.assistant.proposal import ProposalRejected, apply_proposal, base_declarative_config, validate_proposal
from arena.assistant.templates import propose_from_prompt
from arena.tiers.declarative import validate_tier_config_dict


def _draft(config: dict | None = None) -> dict:
    return {"id": "draft-1", "config_json": config or base_declarative_config("offense")}


def test_apply_proposal_then_tier_validator_passes() -> None:
    proposal = propose_from_prompt(
        "Build an offense that punishes pressure without throwing picks.",
        {},
        session_id="s",
        ip="ip",
    )
    validate_proposal(proposal, current_draft=None)
    merged = apply_proposal(proposal, current_draft=None)
    validate_tier_config_dict(merged)


def test_second_layer_validator_failure_surfaces_as_proposal_rejected() -> None:
    config = base_declarative_config("offense")
    bad_config = copy.deepcopy(config)
    bad_config["red_zone"] = {"default": "unknown_concept"}
    current = _draft(bad_config)
    proposal = propose_from_prompt(
        "We got baited by simulated pressure. What should I change?",
        {"current_draft": current},
        session_id="s",
        ip="ip",
    )
    with pytest.raises(ProposalRejected, match="merged config failed tier validator"):
        validate_proposal(proposal, current_draft=current)
