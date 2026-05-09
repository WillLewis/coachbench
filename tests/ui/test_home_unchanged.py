from __future__ import annotations

import hashlib
from pathlib import Path


BASELINE_SHA256 = {
    "ui/index.html": "53bf82d252b50007de325fe2ffec0aa92f908650bad854ab84fdd834c00c1869",
}


def test_home_entry_file_is_byte_identical_to_p0_4_start() -> None:
    for path, expected in BASELINE_SHA256.items():
        actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert actual == expected
