from __future__ import annotations

import json
from pathlib import Path

from coachbench.contracts import validate_replay_contract
from scripts.build_garage_runner_matrix import build_matrix


def test_garage_runner_matrix_covers_every_preset_matchup(tmp_path: Path) -> None:
    out_dir = tmp_path / "garage_runner"
    index = build_matrix(
        profiles_path=Path("agent_garage/profiles.json"),
        out_dir=out_dir,
        seed_pack_path=Path("tests/fixtures/garage_knob_seeds.json"),
        ui_relative_prefix="../data/garage_runner",
    )

    profiles = json.loads(Path("agent_garage/profiles.json").read_text(encoding="utf-8"))
    expected = len(profiles["offense_archetypes"]) * len(profiles["defense_archetypes"]) * 6

    assert index["matrix_id"] == "garage_runner_matrix_v1"
    assert len(index["seed_pack"]) == 6
    assert len(index["entries"]) == expected
    assert (out_dir / "index.json").exists()

    sample = index["entries"][0]
    replay_path = out_dir / sample["file"]
    assert replay_path.exists()
    validate_replay_contract(json.loads(replay_path.read_text(encoding="utf-8")))
    assert sample["path"].startswith("../data/garage_runner/")
    assert sample["invalid_actions"] == 0
    assert sample["resource_ok"] is True


def test_parameter_glossary_covers_live_profile_parameters() -> None:
    profiles = json.loads(Path("agent_garage/profiles.json").read_text(encoding="utf-8"))
    glossary = json.loads(Path("agent_garage/parameter_glossary.json").read_text(encoding="utf-8"))
    live_parameters = {
        key
        for bucket in profiles.values()
        for profile in bucket.values()
        for key in profile["parameters"]
    }

    assert live_parameters <= set(glossary)
    for key in live_parameters:
        assert glossary[key]["football_terms"]
        assert glossary[key]["ai_terms"]
        assert glossary[key]["before_after_signals"]
