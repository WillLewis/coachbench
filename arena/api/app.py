from __future__ import annotations

import sqlite3
from pathlib import Path

try:
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError:  # pragma: no cover
    FastAPI = None
    StaticFiles = None

from arena.api.deps import ROOT
from arena.storage.registry import connect


def db() -> sqlite3.Connection:
    ROOT.mkdir(parents=True, exist_ok=True)
    return connect(ROOT / "arena.sqlite3")


app = FastAPI(title="CoachBench Local Arena") if FastAPI else None


if app:
    from arena.admin.routes import register_admin_routes
    from arena.api.routes_agents import router as agents_router
    from arena.api.routes_assistant import router as assistant_router
    from arena.api.routes_arena import router as arena_router
    from arena.api.routes_challenges import router as challenges_router
    from arena.api.routes_drafts import router as drafts_router
    from arena.api.routes_identities import router as identities_router
    from arena.api.routes_jobs import router as jobs_router
    from arena.api.routes_leaderboard import router as leaderboard_router
    from arena.api.routes_llm_status import router as llm_status_router
    from arena.api.routes_replays import router as replays_router
    from arena.api.routes_runs import router as runs_router

    app.include_router(agents_router)
    app.include_router(assistant_router)
    app.include_router(arena_router)
    app.include_router(challenges_router)
    app.include_router(drafts_router)
    app.include_router(identities_router)
    app.include_router(jobs_router)
    app.include_router(leaderboard_router)
    app.include_router(llm_status_router)
    app.include_router(replays_router)
    app.include_router(runs_router)
    register_admin_routes(app)

    for route_path, directory in (
        ("/ui", "ui"),
        ("/graph", "graph"),
        ("/agent_garage", "agent_garage"),
        ("/data", "data"),
    ):
        if StaticFiles and Path(directory).exists():
            app.mount(route_path, StaticFiles(directory=directory), name=route_path.strip("/"))
