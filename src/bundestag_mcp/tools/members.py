"""MP information and voting tools."""

import json
from typing import Any

from ..clients.dip import get_dip_client
from ..cache.db import get_cache
from ..utils.formatting import format_mp, format_vote


async def get_mp_info(
    name: str | None = None,
    mp_id: str | None = None,
) -> str:
    """Get information about a member of the German Bundestag.

    Args:
        name: Name of the MP (can be partial)
        mp_id: Bundestag person ID

    Returns:
        JSON string with MP information
    """
    if not name and not mp_id:
        return json.dumps({
            "error": "Please provide either a name or mp_id to search for.",
        }, ensure_ascii=False)

    cache = get_cache()
    cache_params = {"name": name, "mp_id": mp_id}

    # Check cache first
    cached = await cache.get("mp_info", cache_params)
    if cached is not None:
        return _format_mp_results(cached, from_cache=True)

    # Fetch from API
    client = get_dip_client()

    try:
        if mp_id:
            person = client.get_person_by_id(mp_id)
            persons = [person] if person else []
        else:
            persons = client.search_persons(name=name, limit=5)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to search for MP. Please try again.",
        }, ensure_ascii=False)

    # Format results
    formatted = [format_mp(p) for p in persons if p]

    # Cache results
    await cache.set("mp_info", cache_params, formatted)

    return _format_mp_results(formatted, from_cache=False)


async def get_mp_votes(
    mp_id: str | None = None,
    name: str | None = None,
    topic_filter: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    limit: int = 10,
) -> str:
    """Get voting record for a member of parliament.

    Note: The DIP API has limited voting data. For comprehensive voting records,
    the AbgeordnetenWatch API would be more suitable (not yet integrated).

    Args:
        mp_id: Bundestag person ID
        name: Name of the MP (alternative to mp_id)
        topic_filter: Filter votes by topic keywords
        date_start: Start date (YYYY-MM-DD)
        date_end: End date (YYYY-MM-DD)
        limit: Maximum number of results

    Returns:
        JSON string with voting records
    """
    # First, we need to get the MP ID if only name is provided
    if not mp_id and name:
        client = get_dip_client()
        try:
            persons = client.search_persons(name=name, limit=1)
            if persons:
                mp_id = str(persons[0].get("id"))
            else:
                return json.dumps({
                    "error": f"No MP found with name '{name}'",
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "message": "Failed to find MP.",
            }, ensure_ascii=False)

    if not mp_id:
        return json.dumps({
            "error": "Please provide either mp_id or name to look up votes.",
        }, ensure_ascii=False)

    cache = get_cache()
    cache_params = {
        "mp_id": mp_id,
        "topic_filter": topic_filter,
        "date_start": date_start,
        "date_end": date_end,
        "limit": limit,
    }

    # Check cache
    cached = await cache.get("mp_votes", cache_params)
    if cached is not None:
        return _format_vote_results(cached, mp_id, from_cache=True)

    # The DIP API doesn't have a direct votes endpoint per person.
    # We can get activities which may include voting participation.
    client = get_dip_client()

    try:
        activities = client.get_activities(
            person_id=mp_id,
            date_start=date_start,
            date_end=date_end,
            limit=limit,
        )
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to get voting data.",
            "note": "For comprehensive voting records, consider using AbgeordnetenWatch API.",
        }, ensure_ascii=False)

    # Filter by topic if provided
    if topic_filter and activities:
        activities = [
            a for a in activities
            if topic_filter.lower() in str(a).lower()
        ]

    # Format as votes
    formatted = [format_vote(a) for a in activities]

    # Cache results
    await cache.set("mp_votes", cache_params, formatted)

    return _format_vote_results(formatted, mp_id, from_cache=False)


def _format_mp_results(mps: list[dict[str, Any]], from_cache: bool) -> str:
    """Format MP results for LLM consumption."""
    if not mps:
        return json.dumps({
            "count": 0,
            "message": "No members of parliament found matching your search.",
            "mps": [],
        }, ensure_ascii=False, indent=2)

    result = {
        "count": len(mps),
        "cached": from_cache,
        "mps": mps,
    }

    # Create summary
    summary_lines = []
    for mp in mps:
        name = mp.get("name", "Unknown")
        party = mp.get("party", "Unknown party")
        constituency = mp.get("constituency")
        line = f"- {name} ({party})"
        if constituency:
            line += f" - {constituency}"
        summary_lines.append(line)

    result["summary"] = "\n".join(summary_lines)

    return json.dumps(result, ensure_ascii=False, indent=2)


def _format_vote_results(
    votes: list[dict[str, Any]],
    mp_id: str,
    from_cache: bool,
) -> str:
    """Format vote results for LLM consumption."""
    if not votes:
        return json.dumps({
            "mp_id": mp_id,
            "count": 0,
            "message": "No voting records found for this MP in the specified range.",
            "note": "The DIP API has limited voting data. For comprehensive records, consider AbgeordnetenWatch.",
            "votes": [],
        }, ensure_ascii=False, indent=2)

    result = {
        "mp_id": mp_id,
        "count": len(votes),
        "cached": from_cache,
        "votes": votes,
    }

    return json.dumps(result, ensure_ascii=False, indent=2)
