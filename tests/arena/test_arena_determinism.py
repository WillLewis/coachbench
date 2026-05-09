from __future__ import annotations

import json

from arena.runs.arena import run_best_of_n_job
from arena.storage import drafts
from arena.storage.registry import connect


def _config(name: str, side: str) -> dict:
    if side == "offense":
        return {
            "agent_name": name,
            "side": "offense",
            "access_tier": "declarative",
            "risk_tolerance": "medium",
            "red_zone": {"default": "quick_game"},
            "third_down": {"default": "quick_game"},
            "preferred_concepts": ["quick_game", "inside_zone"],
            "avoided_concepts": ["vertical_shot"],
            "adaptation_speed": 0.4,
            "tendency_break_rate": 0.1,
            "constraints": {"max_vertical_shot_rate": 0.0},
        }
    return {
        "agent_name": name,
        "side": "defense",
        "access_tier": "declarative",
        "risk_tolerance": "medium",
        "red_zone": {"default": "redzone_bracket"},
        "third_down": {"default": "simulated_pressure"},
        "preferred_concepts": ["simulated_pressure", "cover3_match"],
        "avoided_concepts": ["zero_pressure"],
        "adaptation_speed": 0.4,
        "tendency_break_rate": 0.1,
        "constraints": {},
    }


def _insert_fixed_draft(conn, draft_id: str, name: str, side: str) -> None:
    drafts.init(conn)
    payload = _config(name, side)
    config_json = drafts.validate_draft_config("declarative", side, payload)
    conn.execute(
        """
        INSERT INTO drafts
        (id, name, version, side_eligibility, tier, config_json, created_at, updated_at)
        VALUES (?, ?, 1, ?, 'declarative', ?, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')
        """,
        (draft_id, name, side, config_json),
    )
    conn.commit()


def _report_bytes(workdir) -> bytes:
    conn = connect(workdir / "arena.sqlite3")
    _insert_fixed_draft(conn, "offense-draft", "Deterministic Offense", "offense")
    _insert_fixed_draft(conn, "defense-draft", "Deterministic Defense", "defense")
    report = run_best_of_n_job(
        conn,
        "deterministic-job",
        {
            "offense_draft_id": "offense-draft",
            "defense_draft_id": "defense-draft",
            "n": 2,
            "seed_pack": [42, 99],
            "max_plays": 4,
        },
    )
    return json.dumps(report, indent=2, sort_keys=True).encode("utf-8")


def test_same_drafts_and_seed_pack_produce_byte_identical_report(tmp_path, monkeypatch) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()

    monkeypatch.chdir(first_dir)
    first = _report_bytes(first_dir)
    monkeypatch.chdir(second_dir)
    second = _report_bytes(second_dir)

    assert first == second
