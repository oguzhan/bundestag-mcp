"""Plenary protocol search tool."""

import json
from typing import Any

from ..clients.dip import get_dip_client
from ..cache.db import get_cache
from ..utils.formatting import format_plenary_protocol


async def get_plenary_protocols(
    keywords: str | None = None,
    speaker: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    limit: int = 10,
) -> str:
    """Search Bundestag plenary debate transcripts (Plenarprotokolle).

    Args:
        keywords: Search keywords to find in debate transcripts
        speaker: Filter by speaker name
        date_start: Start date (YYYY-MM-DD)
        date_end: End date (YYYY-MM-DD)
        limit: Maximum number of results

    Returns:
        JSON string with protocol results
    """
    cache = get_cache()
    cache_params = {
        "keywords": keywords,
        "speaker": speaker,
        "date_start": date_start,
        "date_end": date_end,
        "limit": limit,
    }

    # Check cache first
    cached = await cache.get("plenary_protocols", cache_params)
    if cached is not None:
        return _format_results(cached, from_cache=True)

    # Fetch from API
    client = get_dip_client()

    try:
        protocols = client.search_plenary_protocols(
            keywords=keywords,
            speaker=speaker,
            date_start=date_start,
            date_end=date_end,
            limit=limit,
        )
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to search plenary protocols. Please try again.",
        }, ensure_ascii=False)

    # Format results
    formatted = [format_plenary_protocol(p) for p in protocols]

    # Cache results
    await cache.set("plenary_protocols", cache_params, formatted)

    return _format_results(formatted, from_cache=False)


def _format_results(protocols: list[dict[str, Any]], from_cache: bool) -> str:
    """Format protocol results for LLM consumption."""
    if not protocols:
        return json.dumps({
            "count": 0,
            "message": "No plenary protocols found matching your search criteria.",
            "protocols": [],
        }, ensure_ascii=False, indent=2)

    result = {
        "count": len(protocols),
        "cached": from_cache,
        "protocols": protocols,
    }

    # Create a summary
    summary_lines = []
    for i, protocol in enumerate(protocols, 1):
        date = protocol.get("date", "Unknown date")
        title = protocol.get("title", "")
        session = protocol.get("session_number", "")
        period = protocol.get("period", "")

        line = f"{i}. Session {session} (Period {period}) - {date}"
        if title:
            line += f"\n   {title}"
        if protocol.get("url"):
            line += f"\n   PDF: {protocol['url']}"

        summary_lines.append(line)

    result["summary"] = "\n\n".join(summary_lines)

    return json.dumps(result, ensure_ascii=False, indent=2)
