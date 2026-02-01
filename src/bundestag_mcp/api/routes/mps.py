"""MP (Member of Parliament) related API endpoints."""

import json
from fastapi import APIRouter, Query, Path, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...tools.members import get_mp_info, get_mp_votes
from ...tools.voting import get_mp_voting_history

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/mps/{name}")
@limiter.limit("100/minute")
async def get_mp(
    request: Request,
    name: str = Path(..., description="Name of the MP (e.g., 'Scholz', 'Merz')"),
):
    """Get information about a member of the Bundestag.

    Returns party affiliation, constituency, committees, and biographical information.
    """
    result = await get_mp_info(name=name)
    return json.loads(result)


@router.get("/mps/{name}/votes")
@limiter.limit("60/minute")
async def get_mp_voting_record(
    request: Request,
    name: str = Path(..., description="Name of the MP"),
    topic: str | None = Query(None, description="Filter by topic"),
    limit: int = Query(20, ge=1, le=50, description="Maximum votes to return"),
):
    """Get voting history for a specific MP.

    Shows exactly how this person voted on recorded votes.
    """
    result = await get_mp_voting_history(name=name, topic=topic, limit=limit)
    return json.loads(result)


@router.get("/mps/{name}/dip-votes")
@limiter.limit("60/minute")
async def get_mp_dip_votes(
    request: Request,
    name: str = Path(..., description="Name of the MP"),
    topic_filter: str | None = Query(None, description="Filter votes by topic"),
    date_start: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
):
    """Get voting record from DIP (official Bundestag source).

    Alternative source for MP voting data from official Bundestag records.
    """
    result = await get_mp_votes(
        name=name,
        topic_filter=topic_filter,
        date_start=date_start,
        date_end=date_end,
        limit=limit,
    )
    return json.loads(result)
