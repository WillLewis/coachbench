from __future__ import annotations

from fastapi import APIRouter

from arena.api.deps import error
from coachbench.identities import get_identity, identity_to_dict, load_identities


router = APIRouter()


@router.get("/v1/identities")
def list_identities() -> dict:
    return {"identities": [identity_to_dict(identity) for identity in load_identities()]}


@router.get("/v1/identities/{identity_id}")
def read_identity(identity_id: str) -> dict:
    try:
        identity = get_identity(identity_id)
    except KeyError:
        error("not_found", "identity not found", 404)
    return {"identity": identity_to_dict(identity)}
