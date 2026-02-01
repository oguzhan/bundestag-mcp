"""Vote-related API endpoints."""

import json
from fastapi import APIRouter, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...tools.voting import (
    get_roll_call_votes,
    get_vote_details,
    compare_party_votes,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/votes")
@limiter.limit("100/minute")
async def list_votes(
    request: Request,
    topic: str | None = Query(None, description="Filter by topic keyword (e.g., 'Migration', 'Klima')"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
):
    """Get roll-call votes (namentliche Abstimmungen) from the Bundestag.

    Returns votes where every MP's individual vote is recorded.
    """
    result = await get_roll_call_votes(topic=topic, limit=limit)
    return json.loads(result)


@router.get("/votes/{poll_id}")
@limiter.limit("100/minute")
async def get_vote(
    request: Request,
    poll_id: int,
):
    """Get detailed party-by-party breakdown of a specific vote.

    Shows exactly how each party voted on this issue.
    """
    result = await get_vote_details(poll_id=poll_id)
    return json.loads(result)


@router.get("/votes/compare")
@limiter.limit("60/minute")
async def compare_votes(
    request: Request,
    topic: str = Query(..., description="Topic to analyze (e.g., 'Migration', 'Klima')"),
    limit: int = Query(5, ge=1, le=20, description="Number of recent votes to analyze"),
):
    """Compare how different parties voted on a topic across multiple votes.

    Shows voting patterns across parties for a given topic.
    """
    result = await compare_party_votes(topic=topic, limit=limit)
    return json.loads(result)
