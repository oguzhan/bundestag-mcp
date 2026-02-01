"""Party-related API endpoints."""

import json
from fastapi import APIRouter, Query, Path, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...tools.voting import (
    get_party_alignment_score,
    get_absence_rates,
    get_party_unity_scores,
    find_rebel_mps,
    check_party_consistency,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/parties/alignment")
@limiter.limit("60/minute")
async def get_alignment(
    request: Request,
    party1: str | None = Query(None, description="First party (e.g., 'CDU/CSU', 'SPD')"),
    party2: str | None = Query(None, description="Second party (e.g., 'AfD', 'Grüne')"),
    limit: int = Query(20, ge=1, le=50, description="Number of votes to analyze"),
):
    """Calculate voting alignment between parties.

    If party1 and party2 are provided, returns alignment between those two parties.
    If not provided, returns a matrix of all party alignments.
    """
    if party1 and party2:
        result = await get_party_alignment_score(party1=party1, party2=party2, limit=limit)
        return json.loads(result)

    # Return full matrix - compute all pairs
    parties = ["CDU/CSU", "SPD", "Grüne", "FDP", "AfD", "Die Linke"]
    matrix = {}

    for p1 in parties:
        matrix[p1] = {}
        for p2 in parties:
            if p1 == p2:
                matrix[p1][p2] = 100.0
            else:
                result = await get_party_alignment_score(party1=p1, party2=p2, limit=limit)
                data = json.loads(result)
                matrix[p1][p2] = data.get("alignment_score", 0)

    return {"matrix": matrix, "parties": parties, "votes_analyzed": limit}


@router.get("/parties/unity")
@limiter.limit("60/minute")
async def get_unity(
    request: Request,
    limit: int = Query(20, ge=1, le=50, description="Number of votes to analyze"),
):
    """Calculate internal voting unity for each party.

    Shows what percentage of each party votes with their majority.
    """
    result = await get_party_unity_scores(limit=limit)
    return json.loads(result)


@router.get("/parties/absence")
@limiter.limit("60/minute")
async def get_absence(
    request: Request,
    limit: int = Query(20, ge=1, le=50, description="Number of votes to analyze"),
):
    """Get absence/no-show rates for each party.

    Shows which parties skip the most votes.
    """
    result = await get_absence_rates(limit=limit)
    return json.loads(result)


@router.get("/parties/{party}/consistency")
@limiter.limit("60/minute")
async def get_consistency(
    request: Request,
    party: str = Path(..., description="Party name (e.g., 'CDU/CSU', 'SPD', 'AfD')"),
    topic: str = Query(..., description="Topic to check (e.g., 'Migration', 'Klima')"),
    limit: int = Query(10, ge=1, le=30, description="Number of votes to analyze"),
):
    """Check if a party votes consistently on a topic.

    Analyzes whether a party's voting pattern is consistent across multiple votes on a topic.
    """
    result = await check_party_consistency(party=party, topic=topic, limit=limit)
    return json.loads(result)


@router.get("/parties/{party}/rebels")
@limiter.limit("60/minute")
async def get_rebels(
    request: Request,
    party: str = Path(..., description="Party name (e.g., 'CDU/CSU', 'SPD')"),
    limit: int = Query(10, ge=1, le=30, description="Number of votes to analyze"),
):
    """Find MPs who vote against their party most often.

    Identifies dissenters and independent thinkers within a party.
    """
    result = await find_rebel_mps(party=party, limit=limit)
    return json.loads(result)
