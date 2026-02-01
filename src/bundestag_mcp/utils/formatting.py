"""Formatting utilities for LLM-friendly responses."""

from typing import Any


def format_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Format a document for LLM consumption."""
    return {
        "id": doc.get("id"),
        "title": doc.get("titel") or doc.get("title"),
        "type": doc.get("dokumentart") or doc.get("drucksachetyp"),
        "date": doc.get("datum") or doc.get("date"),
        "abstract": doc.get("abstract") or doc.get("zusammenfassung"),
        "url": doc.get("fundstelle", {}).get("pdf_url") if isinstance(doc.get("fundstelle"), dict) else None,
        "authors": doc.get("autoren") or doc.get("authors", []),
    }


def format_mp(person: dict[str, Any]) -> dict[str, Any]:
    """Format an MP profile for LLM consumption."""
    return {
        "id": person.get("id"),
        "name": f"{person.get('vorname', '')} {person.get('nachname', '')}".strip() or person.get("name"),
        "party": person.get("fraktion") or person.get("party"),
        "role": person.get("funktion") or person.get("role"),
        "constituency": person.get("wahlkreis") or person.get("constituency"),
        "state": person.get("bundesland") or person.get("state"),
        "biography": person.get("biografie") or person.get("biography"),
    }


def format_procedure(proc: dict[str, Any]) -> dict[str, Any]:
    """Format a legislative procedure for LLM consumption."""
    return {
        "id": proc.get("id"),
        "title": proc.get("titel") or proc.get("title"),
        "type": proc.get("vorgangstyp") or proc.get("type"),
        "status": _extract_status(proc),
        "initiative": proc.get("initiative"),
        "date_started": proc.get("datum") or proc.get("date"),
        "abstract": proc.get("abstract"),
        "current_step": _get_current_step(proc),
    }


def format_plenary_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    """Format a plenary protocol for LLM consumption."""
    return {
        "id": protocol.get("id"),
        "date": protocol.get("datum") or protocol.get("date"),
        "title": protocol.get("titel") or protocol.get("title"),
        "period": protocol.get("wahlperiode"),
        "session_number": protocol.get("sitzungsnummer"),
        "url": protocol.get("fundstelle", {}).get("pdf_url") if isinstance(protocol.get("fundstelle"), dict) else None,
    }


def format_vote(vote: dict[str, Any]) -> dict[str, Any]:
    """Format a vote record for LLM consumption."""
    return {
        "date": vote.get("datum") or vote.get("date"),
        "topic": vote.get("titel") or vote.get("title") or vote.get("topic"),
        "vote": vote.get("abstimmung") or vote.get("vote"),
        "result": vote.get("ergebnis") or vote.get("result"),
    }


def _extract_status(proc: dict[str, Any]) -> str:
    """Extract the current status from a procedure."""
    beratungsstand = proc.get("beratungsstand")
    if beratungsstand:
        return beratungsstand

    stand = proc.get("stand")
    if stand:
        return stand

    return "Unknown"


def _get_current_step(proc: dict[str, Any]) -> str | None:
    """Get the most recent step in a procedure."""
    verlauf = proc.get("verlauf") or proc.get("steps", [])
    if verlauf and isinstance(verlauf, list) and len(verlauf) > 0:
        latest = verlauf[-1]
        return latest.get("beschreibung") or latest.get("description")
    return None
