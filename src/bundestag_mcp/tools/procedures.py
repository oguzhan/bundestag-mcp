"""Legislative procedures search tool."""

import json
from typing import Any

from ..clients.dip import get_dip_client
from ..cache.db import get_cache
from ..utils.formatting import format_procedure


async def search_procedures(
    keywords: str,
    status: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    limit: int = 10,
) -> str:
    """Search for legislative procedures (Vorgänge) in the Bundestag.

    Args:
        keywords: Search keywords for procedure title or content
        status: Filter by status
        date_start: Start date (YYYY-MM-DD)
        date_end: End date (YYYY-MM-DD)
        limit: Maximum number of results

    Returns:
        JSON string with procedure results
    """
    cache = get_cache()
    cache_params = {
        "keywords": keywords,
        "status": status,
        "date_start": date_start,
        "date_end": date_end,
        "limit": limit,
    }

    # Check cache first
    cached = await cache.get("procedures", cache_params)
    if cached is not None:
        return _format_results(cached, from_cache=True)

    # Fetch from API
    client = get_dip_client()

    try:
        procedures = client.search_procedures(
            keywords=keywords,
            status=status,
            date_start=date_start,
            date_end=date_end,
            limit=limit,
        )
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to search procedures. Please try again.",
        }, ensure_ascii=False)

    # Format results
    formatted = [format_procedure(proc) for proc in procedures]

    # Cache results
    await cache.set("procedures", cache_params, formatted)

    return _format_results(formatted, from_cache=False)


def _format_results(procedures: list[dict[str, Any]], from_cache: bool) -> str:
    """Format procedure results for LLM consumption."""
    if not procedures:
        return json.dumps({
            "count": 0,
            "message": "No legislative procedures found matching your search criteria.",
            "procedures": [],
        }, ensure_ascii=False, indent=2)

    result = {
        "count": len(procedures),
        "cached": from_cache,
        "procedures": procedures,
    }

    # Create a summary for easier LLM processing
    summary_lines = []
    for i, proc in enumerate(procedures, 1):
        title = proc.get("title", "Untitled")
        status = proc.get("status", "Unknown status")
        proc_type = proc.get("type", "")

        # Truncate long titles
        if len(title) > 80:
            title = title[:77] + "..."

        line = f"{i}. {title}"
        if proc_type:
            line = f"{i}. [{proc_type}] {title}"
        line += f"\n   Status: {status}"

        if proc.get("current_step"):
            line += f"\n   Current step: {proc['current_step']}"

        summary_lines.append(line)

    result["summary"] = "\n\n".join(summary_lines)

    return json.dumps(result, ensure_ascii=False, indent=2)
