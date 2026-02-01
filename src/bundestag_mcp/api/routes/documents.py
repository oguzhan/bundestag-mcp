"""Document and procedure related API endpoints."""

import json
from fastapi import APIRouter, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...tools.documents import search_documents
from ...tools.procedures import search_procedures
from ...tools.plenary import get_plenary_protocols
from ...tools.calendar import get_current_week

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/documents")
@limiter.limit("100/minute")
async def list_documents(
    request: Request,
    keywords: str = Query(..., description="Search keywords (German or English)"),
    date_start: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    document_type: str | None = Query(
        None,
        description="Type: 'Gesetzentwurf' (bill), 'Antrag' (motion), 'Kleine Anfrage', 'Große Anfrage'",
    ),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
):
    """Search parliamentary documents (Drucksachen).

    Find bills, motions, reports, and answers to parliamentary questions.
    """
    result = await search_documents(
        keywords=keywords,
        date_start=date_start,
        date_end=date_end,
        document_type=document_type,
        limit=limit,
    )
    return json.loads(result)


@router.get("/procedures")
@limiter.limit("100/minute")
async def list_procedures(
    request: Request,
    keywords: str = Query(..., description="Search keywords"),
    status: str | None = Query(
        None,
        description="Filter by status: 'Noch nicht beraten', 'Überwiesen', 'Abgeschlossen'",
    ),
    date_start: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
):
    """Track legislative procedures (Vorgänge).

    Shows the status and progress of bills and other parliamentary procedures.
    """
    result = await search_procedures(
        keywords=keywords,
        status=status,
        date_start=date_start,
        date_end=date_end,
        limit=limit,
    )
    return json.loads(result)


@router.get("/protocols")
@limiter.limit("100/minute")
async def list_protocols(
    request: Request,
    keywords: str | None = Query(None, description="Search keywords in transcripts"),
    speaker: str | None = Query(None, description="Filter by speaker name"),
    date_start: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
):
    """Access plenary debate transcripts (Plenarprotokolle).

    Search speeches and debates by topic or speaker.
    """
    result = await get_plenary_protocols(
        keywords=keywords,
        speaker=speaker,
        date_start=date_start,
        date_end=date_end,
        limit=limit,
    )
    return json.loads(result)


@router.get("/calendar/week")
@limiter.limit("100/minute")
async def get_week(request: Request):
    """Get the current week's Bundestag schedule.

    Shows scheduled plenary debates, votes, and committee meetings.
    """
    result = await get_current_week()
    return json.loads(result)
