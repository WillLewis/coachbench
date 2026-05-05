from __future__ import annotations

import sqlite3

try:
    from fastapi import FastAPI
except ModuleNotFoundError:  # pragma: no cover
    FastAPI = None

from arena.api.deps import ROOT
from arena.storage.registry import connect


def db() -> sqlite3.Connection:
    ROOT.mkdir(parents=True, exist_ok=True)
    return connect(ROOT / "arena.sqlite3")


app = FastAPI(title="CoachBench Local Arena") if FastAPI else None


if app:
    from arena.admin.routes import register_admin_routes
    from arena.api.routes_agents import router as agents_router
    from arena.api.routes_challenges import router as challenges_router
    from arena.api.routes_jobs import router as jobs_router
    from arena.api.routes_leaderboard import router as leaderboard_router

    app.include_router(agents_router)
    app.include_router(challenges_router)
    app.include_router(jobs_router)
    app.include_router(leaderboard_router)
    register_admin_routes(app)
