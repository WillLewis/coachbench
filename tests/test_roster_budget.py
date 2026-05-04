from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from coachbench.contracts import ContractValidationError, validate_roster_budget
from coachbench.roster_budget import load_roster


ROSTER_PATHS = [
    Path("data/rosters/balanced_v0.json"),
    Path("data/rosters/pass_heavy_v0.json"),
    Path("data/rosters/defense_heavy_v0.json"),
]


def _payload(path: Path = ROSTER_PATHS[0]) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_roster_templates_load_and_validate() -> None:
    for path in ROSTER_PATHS:
        payload = _payload(path)
        validate_roster_budget(payload)
        roster = load_roster(path)
        assert roster.budget_points == 300
        assert sum(roster.values.values()) == 300


def test_roster_rejects_overspend() -> None:
    payload = _payload()
    payload["position_groups"]["qb"]["value"] = 51
    with pytest.raises(ContractValidationError, match="does not equal budget_points"):
        validate_roster_budget(payload)


def test_roster_rejects_underspend() -> None:
    payload = _payload()
    payload["position_groups"]["qb"]["value"] = 49
    with pytest.raises(ContractValidationError, match="does not equal budget_points"):
        validate_roster_budget(payload)


def test_roster_rejects_unknown_group() -> None:
    payload = _payload()
    payload["position_groups"] = deepcopy(payload["position_groups"])
    payload["position_groups"]["specialists"] = {"trait": "local_depth", "value": 0}
    with pytest.raises(ContractValidationError, match="groups invalid"):
        validate_roster_budget(payload)
