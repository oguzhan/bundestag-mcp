"""MCP tools for Bundestag data access."""

from .documents import search_documents
from .members import get_mp_info, get_mp_votes
from .procedures import search_procedures
from .plenary import get_plenary_protocols
from .calendar import get_current_week
from .voting import (
    get_roll_call_votes,
    get_vote_details,
    compare_party_votes,
    get_mp_voting_history,
    check_party_consistency,
    # Advanced analytical tools
    get_party_alignment_score,
    get_absence_rates,
    get_party_unity_scores,
    find_rebel_mps,
)

__all__ = [
    # Core tools
    "search_documents",
    "get_mp_info",
    "get_mp_votes",
    "search_procedures",
    "get_plenary_protocols",
    "get_current_week",
    # Voting "truth" tools
    "get_roll_call_votes",
    "get_vote_details",
    "compare_party_votes",
    "get_mp_voting_history",
    "check_party_consistency",
    # Advanced analytical tools
    "get_party_alignment_score",
    "get_absence_rates",
    "get_party_unity_scores",
    "find_rebel_mps",
]
