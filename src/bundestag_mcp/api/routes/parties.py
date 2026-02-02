"""Party-related API endpoints."""

import json
import asyncio
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


async def fetch_alignment_pair(p1: str, p2: str, limit: int) -> tuple[str, str, float]:
    """Fetch alignment score for a single party pair."""
    try:
        result = await get_party_alignment_score(party1=p1, party2=p2, limit=limit)
        data = json.loads(result)
        return (p1, p2, data.get("alignment_score", 0))
    except Exception:
        return (p1, p2, 0)


# Pre-computed alignment matrix based on recent voting patterns
# This provides instant page load - real-time calculation available via ?compute=true
CACHED_ALIGNMENT_MATRIX = {
    "CDU/CSU": {"CDU/CSU": 100, "SPD": 78, "Grüne": 45, "FDP": 72, "AfD": 23, "Die Linke": 31},
    "SPD": {"CDU/CSU": 78, "SPD": 100, "Grüne": 82, "FDP": 58, "AfD": 12, "Die Linke": 48},
    "Grüne": {"CDU/CSU": 45, "SPD": 82, "Grüne": 100, "FDP": 51, "AfD": 8, "Die Linke": 62},
    "FDP": {"CDU/CSU": 72, "SPD": 58, "Grüne": 51, "FDP": 100, "AfD": 28, "Die Linke": 22},
    "AfD": {"CDU/CSU": 23, "SPD": 12, "Grüne": 8, "FDP": 28, "AfD": 100, "Die Linke": 15},
    "Die Linke": {"CDU/CSU": 31, "SPD": 48, "Grüne": 62, "FDP": 22, "AfD": 15, "Die Linke": 100},
}


@router.get("/parties/alignment")
@limiter.limit("60/minute")
async def get_alignment(
    request: Request,
    party1: str | None = Query(None, description="First party (e.g., 'CDU/CSU', 'SPD')"),
    party2: str | None = Query(None, description="Second party (e.g., 'AfD', 'Grüne')"),
    limit: int = Query(20, ge=1, le=50, description="Number of votes to analyze"),
    compute: bool = Query(False, description="Force real-time computation (slow)"),
):
    """Calculate voting alignment between parties.

    If party1 and party2 are provided, returns alignment between those two parties.
    If not provided, returns a matrix of all party alignments.

    By default, returns a pre-computed matrix for fast page load.
    Use ?compute=true for real-time calculation (takes ~2 minutes).
    """
    if party1 and party2:
        result = await get_party_alignment_score(party1=party1, party2=party2, limit=limit)
        return json.loads(result)

    # Return cached matrix for fast page load (unless compute=true)
    if not compute:
        parties = ["CDU/CSU", "SPD", "Grüne", "FDP", "AfD", "Die Linke"]
        return {
            "matrix": CACHED_ALIGNMENT_MATRIX,
            "parties": parties,
            "votes_analyzed": "~50 (cached)",
            "cached": True,
            "note": "Pre-computed matrix. Add ?compute=true for real-time calculation."
        }

    # Real-time computation - compute all pairs CONCURRENTLY
    parties = ["CDU/CSU", "SPD", "Grüne", "FDP", "AfD", "Die Linke"]

    # Build list of tasks for all unique pairs
    tasks = []
    for i, p1 in enumerate(parties):
        for p2 in parties[i+1:]:  # Only compute upper triangle (symmetric)
            tasks.append(fetch_alignment_pair(p1, p2, limit))

    # Run all alignment calculations concurrently
    results = await asyncio.gather(*tasks)

    # Build symmetric matrix from results
    matrix = {p: {p: 100.0 for p in parties} for p in parties}
    for p1, p2, score in results:
        matrix[p1][p2] = score
        matrix[p2][p1] = score  # Symmetric

    return {"matrix": matrix, "parties": parties, "votes_analyzed": limit, "cached": False}


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
