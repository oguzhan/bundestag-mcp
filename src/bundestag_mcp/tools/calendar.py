"""Calendar and scheduling tools."""

import json
from datetime import datetime, timedelta
from typing import Any

from ..clients.dip import get_dip_client
from ..cache.db import get_cache


async def get_current_week() -> str:
    """Get the current week's Bundestag schedule.

    Returns scheduled plenary debates, documents, and activities for
    the current week.

    Returns:
        JSON string with this week's schedule
    """
    today = datetime.now()

    # Calculate the start of the week (Monday)
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)

    # Calculate end of week (Sunday)
    week_end = week_start + timedelta(days=6)

    date_start = week_start.strftime("%Y-%m-%d")
    date_end = week_end.strftime("%Y-%m-%d")

    cache = get_cache()
    cache_params = {"week_start": date_start}

    # Check cache (shorter TTL for current week data)
    cached = await cache.get("current_week", cache_params)
    if cached is not None:
        return _format_week_results(cached, date_start, date_end, from_cache=True)

    client = get_dip_client()
    week_data: dict[str, Any] = {
        "documents": [],
        "procedures": [],
        "protocols": [],
    }

    # Fetch recent documents
    try:
        docs = client.search_documents(
            date_start=date_start,
            date_end=date_end,
            limit=20,
        )
        week_data["documents"] = [
            {
                "id": d.get("id"),
                "title": d.get("titel") or d.get("title"),
                "type": d.get("dokumentart") or d.get("drucksachetyp"),
                "date": d.get("datum") or d.get("date"),
            }
            for d in docs
        ]
    except Exception:
        pass

    # Fetch recent procedures
    try:
        procs = client.search_procedures(
            date_start=date_start,
            date_end=date_end,
            limit=20,
        )
        week_data["procedures"] = [
            {
                "id": p.get("id"),
                "title": p.get("titel") or p.get("title"),
                "type": p.get("vorgangstyp"),
                "status": p.get("beratungsstand"),
            }
            for p in procs
        ]
    except Exception:
        pass

    # Fetch plenary protocols for this week
    try:
        protocols = client.search_plenary_protocols(
            date_start=date_start,
            date_end=date_end,
            limit=10,
        )
        week_data["protocols"] = [
            {
                "id": p.get("id"),
                "date": p.get("datum") or p.get("date"),
                "session": p.get("sitzungsnummer"),
                "title": p.get("titel") or p.get("title"),
            }
            for p in protocols
        ]
    except Exception:
        pass

    # Cache with shorter TTL (4 hours for current week data)
    await cache.set("current_week", cache_params, [week_data], ttl_hours=4)

    return _format_week_results([week_data], date_start, date_end, from_cache=False)


def _format_week_results(
    data: list[dict[str, Any]],
    date_start: str,
    date_end: str,
    from_cache: bool,
) -> str:
    """Format week results for LLM consumption."""
    if not data:
        data = [{"documents": [], "procedures": [], "protocols": []}]

    week_data = data[0]

    result = {
        "week": {
            "start": date_start,
            "end": date_end,
        },
        "cached": from_cache,
        "plenary_sessions": week_data.get("protocols", []),
        "new_documents": week_data.get("documents", []),
        "active_procedures": week_data.get("procedures", []),
    }

    # Create a human-readable summary
    summary_parts = []

    summary_parts.append(f"Bundestag Week: {date_start} to {date_end}")
    summary_parts.append("=" * 40)

    # Plenary sessions
    protocols = week_data.get("protocols", [])
    if protocols:
        summary_parts.append(f"\nPlenary Sessions ({len(protocols)}):")
        for p in protocols[:5]:
            session = p.get("session")
            date = p.get("date", "")
            title = p.get("title", "")
            summary_parts.append(f"  - Session {session} ({date}): {title}")
    else:
        summary_parts.append("\nNo plenary sessions scheduled for this week.")

    # New documents
    docs = week_data.get("documents", [])
    if docs:
        summary_parts.append(f"\nNew Documents ({len(docs)}):")
        for d in docs[:5]:
            doc_type = d.get("type", "Document")
            title = d.get("title", "Untitled")
            if len(title) > 60:
                title = title[:57] + "..."
            summary_parts.append(f"  - [{doc_type}] {title}")
        if len(docs) > 5:
            summary_parts.append(f"  ... and {len(docs) - 5} more documents")
    else:
        summary_parts.append("\nNo new documents published this week.")

    # Active procedures
    procs = week_data.get("procedures", [])
    if procs:
        summary_parts.append(f"\nActive Procedures ({len(procs)}):")
        for p in procs[:5]:
            title = p.get("title", "Untitled")
            status = p.get("status", "")
            if len(title) > 60:
                title = title[:57] + "..."
            summary_parts.append(f"  - {title}")
            if status:
                summary_parts.append(f"    Status: {status}")
        if len(procs) > 5:
            summary_parts.append(f"  ... and {len(procs) - 5} more procedures")
    else:
        summary_parts.append("\nNo active procedures this week.")

    result["summary"] = "\n".join(summary_parts)

    return json.dumps(result, ensure_ascii=False, indent=2)
