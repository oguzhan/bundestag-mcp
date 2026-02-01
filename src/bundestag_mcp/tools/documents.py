"""Document search tool for Bundestag parliamentary documents."""

import json
from typing import Any

from ..clients.dip import get_dip_client
from ..cache.db import get_cache
from ..utils.formatting import format_document


async def search_documents(
    keywords: str,
    date_start: str | None = None,
    date_end: str | None = None,
    document_type: str | None = None,
    limit: int = 10,
) -> str:
    """Search German Bundestag parliamentary documents (Drucksachen).

    Args:
        keywords: Search keywords
        date_start: Start date (YYYY-MM-DD)
        date_end: End date (YYYY-MM-DD)
        document_type: Type of document to filter
        limit: Maximum number of results

    Returns:
        JSON string with search results
    """
    cache = get_cache()
    cache_params = {
        "keywords": keywords,
        "date_start": date_start,
        "date_end": date_end,
        "document_type": document_type,
        "limit": limit,
    }

    # Check cache first
    cached = await cache.get("documents", cache_params)
    if cached is not None:
        return _format_results(cached, from_cache=True)

    # Fetch from API
    client = get_dip_client()
    try:
        documents = client.search_documents(
            keywords=keywords,
            date_start=date_start,
            date_end=date_end,
            document_type=document_type,
            limit=limit,
        )
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to search documents. Please try again.",
        }, ensure_ascii=False)

    # Format results
    formatted = [format_document(doc) for doc in documents]

    # Cache results
    await cache.set("documents", cache_params, formatted)

    return _format_results(formatted, from_cache=False)


def _format_results(documents: list[dict[str, Any]], from_cache: bool) -> str:
    """Format document results for LLM consumption."""
    if not documents:
        return json.dumps({
            "count": 0,
            "message": "No documents found matching your search criteria.",
            "documents": [],
        }, ensure_ascii=False, indent=2)

    result = {
        "count": len(documents),
        "cached": from_cache,
        "documents": documents,
    }

    # Create a summary for easier LLM processing
    summary_lines = []
    for i, doc in enumerate(documents, 1):
        title = doc.get("title", "Untitled")
        doc_type = doc.get("type", "Unknown type")
        date = doc.get("date", "Unknown date")
        summary_lines.append(f"{i}. [{doc_type}] {title} ({date})")

    result["summary"] = "\n".join(summary_lines)

    return json.dumps(result, ensure_ascii=False, indent=2)
