"""Bundestag MCP Server - Main entry point."""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools import (
    search_documents,
    get_mp_info,
    get_mp_votes,
    search_procedures,
    get_plenary_protocols,
    get_current_week,
    # Voting "truth" tools
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Server("bundestag-mcp")


TOOLS = [
    Tool(
        name="search_documents",
        description="Search German Bundestag parliamentary documents (Drucksachen). Returns documents matching your query including bills, motions, reports, and answers to parliamentary questions.",
        inputSchema={
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Search keywords (German or English). Example: 'Klimaschutz' or 'climate protection'"
                },
                "date_start": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "date_end": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
                "document_type": {
                    "type": "string",
                    "description": "Type of document: 'Gesetzentwurf' (bill), 'Antrag' (motion), 'Kleine Anfrage' (minor interpellation), 'Große Anfrage' (major interpellation)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10, max: 50)",
                    "default": 10
                }
            },
            "required": ["keywords"]
        }
    ),
    Tool(
        name="search_procedures",
        description="Track legislative processes (Vorgänge) in the Bundestag. Shows the status and progress of bills and other parliamentary procedures.",
        inputSchema={
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Search keywords for the procedure title or content"
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status. Options: 'Noch nicht beraten' (not yet discussed), 'Im Bundestag noch nicht beraten' (pending in Bundestag), 'Überwiesen' (referred to committee), 'Beschlussempfehlung liegt vor' (committee recommendation available), 'Abgeschlossen' (concluded)"
                },
                "date_start": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "date_end": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)",
                    "default": 10
                }
            },
            "required": ["keywords"]
        }
    ),
    Tool(
        name="get_plenary_protocols",
        description="Access Bundestag plenary debate transcripts (Plenarprotokolle). Search speeches and debates by topic or speaker.",
        inputSchema={
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Search keywords to find in debate transcripts"
                },
                "speaker": {
                    "type": "string",
                    "description": "Filter by speaker name"
                },
                "date_start": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "date_end": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)",
                    "default": 10
                }
            }
        }
    ),
    Tool(
        name="get_mp_info",
        description="Get information about a member of the German Bundestag (MdB). Returns party affiliation, constituency, committees, and biographical information.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the MP (can be partial, e.g., 'Scholz' or 'Olaf Scholz')"
                },
                "mp_id": {
                    "type": "string",
                    "description": "Bundestag person ID (if known)"
                }
            }
        }
    ),
    Tool(
        name="get_mp_votes",
        description="Get voting record for a member of parliament. Shows how they voted on specific issues.",
        inputSchema={
            "type": "object",
            "properties": {
                "mp_id": {
                    "type": "string",
                    "description": "Bundestag person ID"
                },
                "name": {
                    "type": "string",
                    "description": "Name of the MP (alternative to mp_id)"
                },
                "topic_filter": {
                    "type": "string",
                    "description": "Filter votes by topic keywords"
                },
                "date_start": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "date_end": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)",
                    "default": 10
                }
            }
        }
    ),
    Tool(
        name="get_current_week",
        description="Get the current week's Bundestag schedule. Shows scheduled plenary debates, votes, and committee meetings.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    # === VOTING "TRUTH" TOOLS ===
    # These tools expose how politicians actually vote vs what they say
    Tool(
        name="get_roll_call_votes",
        description="Get roll-call votes (namentliche Abstimmungen) where every MP's vote is recorded. Use this to see what was actually voted on and the results. This is the foundation for checking political 'truth'.",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Filter by topic keyword (e.g., 'Migration', 'Klima', 'Rente', 'Wohnen')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)",
                    "default": 10
                }
            }
        }
    ),
    Tool(
        name="get_vote_details",
        description="Get detailed party-by-party breakdown of a specific vote. Shows exactly how each party voted - the 'truth' of their position on an issue.",
        inputSchema={
            "type": "object",
            "properties": {
                "poll_id": {
                    "type": "integer",
                    "description": "The poll/vote ID (get this from get_roll_call_votes)"
                }
            },
            "required": ["poll_id"]
        }
    ),
    Tool(
        name="compare_party_votes",
        description="Compare how different parties voted on a topic across multiple votes. Exposes the gap between what parties SAY and how they actually VOTE.",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to analyze (e.g., 'Migration', 'Klima', 'Soziales', 'Rente')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recent votes to analyze (default: 5)",
                    "default": 5
                }
            },
            "required": ["topic"]
        }
    ),
    Tool(
        name="get_mp_voting_history",
        description="Get detailed voting history for a specific MP. Shows exactly how this person voted - not what they said in interviews or talk shows.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "MP's name (e.g., 'Merz', 'Scholz', 'Weidel', 'Habeck')"
                },
                "topic": {
                    "type": "string",
                    "description": "Optional topic filter"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum votes to return (default: 20)",
                    "default": 20
                }
            },
            "required": ["name"]
        }
    ),
    Tool(
        name="check_party_consistency",
        description="Check if a party votes consistently on a topic. This is the key 'truth' tool - exposes hypocrisy between public statements and actual votes.",
        inputSchema={
            "type": "object",
            "properties": {
                "party": {
                    "type": "string",
                    "description": "Party name (e.g., 'CDU/CSU', 'SPD', 'AfD', 'Grüne', 'Die Linke', 'BSW')"
                },
                "topic": {
                    "type": "string",
                    "description": "Topic to check (e.g., 'Migration', 'Klima', 'Rente')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of votes to analyze (default: 10)",
                    "default": 10
                }
            },
            "required": ["party", "topic"]
        }
    ),
    # === ADVANCED ANALYTICAL TOOLS ===
    # These answer questions web search cannot - they compute across data
    Tool(
        name="get_party_alignment_score",
        description="Calculate how often two parties vote the same way. Answers: 'How often do CDU and AfD vote together?' Web search cannot compute this.",
        inputSchema={
            "type": "object",
            "properties": {
                "party1": {
                    "type": "string",
                    "description": "First party (e.g., 'CDU/CSU', 'SPD')"
                },
                "party2": {
                    "type": "string",
                    "description": "Second party (e.g., 'AfD', 'Grüne')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of votes to analyze (default: 20)",
                    "default": 20
                }
            },
            "required": ["party1", "party2"]
        }
    ),
    Tool(
        name="get_absence_rates",
        description="Calculate which parties skip the most votes. Shows no-show rates per party across all recorded votes.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of votes to analyze (default: 20)",
                    "default": 20
                }
            }
        }
    ),
    Tool(
        name="get_party_unity_scores",
        description="Calculate how unified each party votes internally. Shows what percentage of each party votes with their majority - reveals which parties are most/least cohesive.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of votes to analyze (default: 20)",
                    "default": 20
                }
            }
        }
    ),
    Tool(
        name="find_rebel_mps",
        description="Find MPs who vote against their own party most often. Identifies dissenters and free-thinkers within a party.",
        inputSchema={
            "type": "object",
            "properties": {
                "party": {
                    "type": "string",
                    "description": "Party to analyze (e.g., 'CDU/CSU', 'SPD', 'AfD')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of votes to analyze (default: 10)",
                    "default": 10
                }
            },
            "required": ["party"]
        }
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return the list of available tools."""
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with arguments: {arguments}")

    try:
        if name == "search_documents":
            result = await search_documents(**arguments)
        elif name == "search_procedures":
            result = await search_procedures(**arguments)
        elif name == "get_plenary_protocols":
            result = await get_plenary_protocols(**arguments)
        elif name == "get_mp_info":
            result = await get_mp_info(**arguments)
        elif name == "get_mp_votes":
            result = await get_mp_votes(**arguments)
        elif name == "get_current_week":
            result = await get_current_week()
        # Voting "truth" tools
        elif name == "get_roll_call_votes":
            result = await get_roll_call_votes(**arguments)
        elif name == "get_vote_details":
            result = await get_vote_details(**arguments)
        elif name == "compare_party_votes":
            result = await compare_party_votes(**arguments)
        elif name == "get_mp_voting_history":
            result = await get_mp_voting_history(**arguments)
        elif name == "check_party_consistency":
            result = await check_party_consistency(**arguments)
        # Advanced analytical tools
        elif name == "get_party_alignment_score":
            result = await get_party_alignment_score(**arguments)
        elif name == "get_absence_rates":
            result = await get_absence_rates(**arguments)
        elif name == "get_party_unity_scores":
            result = await get_party_unity_scores(**arguments)
        elif name == "find_rebel_mps":
            result = await find_rebel_mps(**arguments)
        else:
            result = f"Unknown tool: {name}"

        return [TextContent(type="text", text=str(result))]

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


def main():
    """Main entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
