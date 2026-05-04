from __future__ import annotations

import pytest

from arena.api.server import validate_bind_host


def test_local_bind_guard_accepts_loopback_and_rejects_public_bind() -> None:
    validate_bind_host("127.0.0.1")
    with pytest.raises(ValueError, match="local mode"):
        validate_bind_host("0.0.0.0")
