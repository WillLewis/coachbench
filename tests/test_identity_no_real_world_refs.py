from __future__ import annotations

from pathlib import Path

from coachbench.identities import BANNED_IDENTITY_TOKENS


LAUNCH_SURFACES = [
    Path("data/identities/launch_identities.json"),
    Path("README.md"),
    Path("arena/README.md"),
    Path("ui/showcase_manifest.json"),
]


def test_launch_identity_surfaces_have_no_prohibited_tokens() -> None:
    hits = []
    for path in LAUNCH_SURFACES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for token in BANNED_IDENTITY_TOKENS:
            if token in text:
                hits.append(f"{path}:{token}")
    assert hits == []
