from __future__ import annotations


LOCAL_BIND_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_bind_host(host: str) -> None:
    if host not in LOCAL_BIND_HOSTS:
        raise ValueError("CoachBench arena local mode only allows binding to 127.0.0.1/localhost")
