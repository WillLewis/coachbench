from __future__ import annotations

import copy

import pytest

from arena.assistant.proposal import ProposalRejected, base_declarative_config, validate_proposal
from arena.assistant.templates import propose_from_prompt


def _draft(side: str = "offense") -> dict:
    return {
        "id": f"{side}-draft",
        "config_json": base_declarative_config(side, agent_name=f"{side} draft"),
    }


def test_valid_proposal_round_trips_every_field() -> None:
    proposal = propose_from_prompt(
        "Build an offense that punishes pressure without throwing picks.",
        {},
        session_id="s",
        ip="127.0.0.1",
    )
    assert set(proposal) == {
        "summary",
        "intent",
        "target_draft_id",
        "target_tier",
        "target_side",
        "target_identity_id",
        "proposed_changes",
        "evidence_refs",
        "requires_confirmation",
    }
    validate_proposal(proposal, current_draft=None)


def test_rejects_unknown_intent() -> None:
    proposal = propose_from_prompt("Build an offense that punishes pressure without throwing picks.", {}, session_id="s", ip="ip")
    proposal["intent"] = "invent"
    with pytest.raises(ProposalRejected):
        validate_proposal(proposal, current_draft=None)


def test_rejects_unknown_parameter() -> None:
    proposal = propose_from_prompt("Build an offense that punishes pressure without throwing picks.", {}, session_id="s", ip="ip")
    proposal["proposed_changes"][0]["parameter"] = "play_action_unlock_threshold"
    with pytest.raises(ProposalRejected):
        validate_proposal(proposal, current_draft=None)


def test_rejects_out_of_range_value() -> None:
    proposal = propose_from_prompt("Build an offense that punishes pressure without throwing picks.", {}, session_id="s", ip="ip")
    proposal["proposed_changes"][0]["to"] = 1.5
    with pytest.raises(ProposalRejected):
        validate_proposal(proposal, current_draft=None)


def test_rejects_unsupported_identity() -> None:
    proposal = propose_from_prompt("Build an offense that punishes pressure without throwing picks.", {}, session_id="s", ip="ip")
    proposal["target_identity_id"] = "unknown_identity"
    with pytest.raises(ProposalRejected):
        validate_proposal(proposal, current_draft=None)


def test_rejects_missing_target_draft_on_tweak() -> None:
    proposal = propose_from_prompt(
        "We got baited by simulated pressure. What should I change?",
        {"current_draft": _draft("offense")},
        session_id="s",
        ip="ip",
    )
    proposal["target_draft_id"] = None
    with pytest.raises(ProposalRejected):
        validate_proposal(proposal, current_draft=None)


def test_rejects_stale_from_value() -> None:
    current = _draft("offense")
    proposal = propose_from_prompt(
        "We got baited by simulated pressure. What should I change?",
        {"current_draft": current},
        session_id="s",
        ip="ip",
    )
    proposal["proposed_changes"][0]["from"] = 0.01
    with pytest.raises(ProposalRejected):
        validate_proposal(proposal, current_draft=current)


def test_clarify_proposals_are_inert() -> None:
    proposal = propose_from_prompt("something vague", {}, session_id="s", ip="ip")
    validate_proposal(proposal, current_draft=None)
    broken = copy.deepcopy(proposal)
    broken["proposed_changes"] = [{"parameter": "risk_tolerance", "from": None, "to": "high", "reason": "bad"}]
    with pytest.raises(ProposalRejected):
        validate_proposal(broken, current_draft=None)
