"""Chat endpoint with Claude AI integration and tool execution."""

import json
import os
from typing import Any
import anthropic
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...tools import (
    search_documents,
    get_mp_info,
    get_mp_votes,
    search_procedures,
    get_plenary_protocols,
    get_current_week,
    get_roll_call_votes,
    get_vote_details,
    compare_party_votes,
    get_mp_voting_history,
    check_party_consistency,
    get_party_alignment_score,
    get_absence_rates,
    get_party_unity_scores,
    find_rebel_mps,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# System prompt for the parliamentary assistant
SYSTEM_PROMPT = """You are a parliamentary research assistant for the German Bundestag.

You have access to official voting records and can analyze:
- Roll-call votes (namentliche Abstimmungen) and their results
- How specific parties voted on issues
- Individual MP voting records and party loyalty
- Party alignment scores (how often parties vote together)
- Party unity and absence rates

IMPORTANT GUIDELINES:
1. Always cite specific votes with their IDs when making claims
2. Be factual and non-partisan - present data, not opinions
3. When asked about how someone or a party voted, ALWAYS use the tools to look up actual data
4. Do not editorialize or add commentary about whether votes are "good" or "bad"
5. If data is unavailable, say so clearly
6. Present numbers and percentages when available
7. Respond in the same language the user writes in (German or English)

PARTY COMPARISON QUERIES:
When users ask to compare two parties (e.g., "Compare AfD vs CDU"), ALWAYS use get_party_alignment_score.
This returns rich data with alignment percentage, shared votes, and disagreements that will be
displayed as an interactive card. Keep your text response brief (1-2 sentences) since the card
provides the detailed breakdown with clickable vote links.

NAVIGATION GUIDANCE:
You can also use suggest_navigation to help users explore more data in the full UI:
- User asks about multiple votes on a topic → suggest votes page with topic filter
- User wants to see the full alignment matrix → suggest parties page
- User asks about an MP → suggest MPs page with that name pre-filled

Examples:
- "Show me climate votes" → suggest_navigation(page="votes", params={topic: "Klima"})
- "Show me the full party matrix" → suggest_navigation(page="parties")
- "Tell me about Olaf Scholz" → suggest_navigation(page="mps", params={search: "Scholz"})

Data sources:
- Voting records: AbgeordnetenWatch (CC0 licensed)
- Parliamentary documents: Official Bundestag DIP API
"""

# Tool definitions for Claude (matching our MCP tools)
CLAUDE_TOOLS = [
    {
        "name": "get_roll_call_votes",
        "description": "Get roll-call votes (namentliche Abstimmungen) where every MP's vote is recorded. Use this to find votes on a topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Filter by topic keyword (e.g., 'Migration', 'Klima', 'Rente', 'Wohnen')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)",
                    "default": 10,
                },
            },
        },
    },
    {
        "name": "get_vote_details",
        "description": "Get detailed party-by-party breakdown of a specific vote. Shows exactly how each party voted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "poll_id": {
                    "type": "integer",
                    "description": "The poll/vote ID (get this from get_roll_call_votes)",
                },
            },
            "required": ["poll_id"],
        },
    },
    {
        "name": "compare_party_votes",
        "description": "Compare how different parties voted on a topic across multiple votes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to analyze (e.g., 'Migration', 'Klima')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recent votes to analyze (default: 5)",
                    "default": 5,
                },
            },
            "required": ["topic"],
        },
    },
    {
        "name": "get_mp_voting_history",
        "description": "Get detailed voting history for a specific MP. Shows exactly how this person voted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "MP's name (e.g., 'Merz', 'Scholz', 'Habeck')",
                },
                "topic": {
                    "type": "string",
                    "description": "Optional topic filter",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum votes to return (default: 20)",
                    "default": 20,
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "check_party_consistency",
        "description": "Check if a party votes consistently on a topic across multiple votes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "party": {
                    "type": "string",
                    "description": "Party name (e.g., 'CDU/CSU', 'SPD', 'AfD', 'Grüne')",
                },
                "topic": {
                    "type": "string",
                    "description": "Topic to check (e.g., 'Migration', 'Klima')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of votes to analyze (default: 10)",
                    "default": 10,
                },
            },
            "required": ["party", "topic"],
        },
    },
    {
        "name": "get_party_alignment_score",
        "description": "Calculate how often two parties vote the same way.",
        "input_schema": {
            "type": "object",
            "properties": {
                "party1": {
                    "type": "string",
                    "description": "First party (e.g., 'CDU/CSU', 'SPD')",
                },
                "party2": {
                    "type": "string",
                    "description": "Second party (e.g., 'AfD', 'Grüne')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of votes to analyze (default: 20)",
                    "default": 20,
                },
            },
            "required": ["party1", "party2"],
        },
    },
    {
        "name": "get_absence_rates",
        "description": "Get absence/no-show rates for each party across all recorded votes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of votes to analyze (default: 20)",
                    "default": 20,
                },
            },
        },
    },
    {
        "name": "get_party_unity_scores",
        "description": "Calculate how unified each party votes internally - what percentage votes with their majority.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of votes to analyze (default: 20)",
                    "default": 20,
                },
            },
        },
    },
    {
        "name": "find_rebel_mps",
        "description": "Find MPs who vote against their own party most often.",
        "input_schema": {
            "type": "object",
            "properties": {
                "party": {
                    "type": "string",
                    "description": "Party to analyze (e.g., 'CDU/CSU', 'SPD')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of votes to analyze (default: 10)",
                    "default": 10,
                },
            },
            "required": ["party"],
        },
    },
    {
        "name": "get_mp_info",
        "description": "Get information about a member of the Bundestag including party, constituency, and committees.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the MP (can be partial)",
                },
            },
        },
    },
    {
        "name": "search_documents",
        "description": "Search parliamentary documents (Drucksachen) including bills, motions, and questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Search keywords",
                },
                "date_start": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD)",
                },
                "date_end": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default: 10)",
                    "default": 10,
                },
            },
            "required": ["keywords"],
        },
    },
    {
        "name": "suggest_navigation",
        "description": "Suggest navigating to a specific page with filters applied. Use this when the user's question would be better answered by viewing the full UI with data visualization.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "string",
                    "enum": ["votes", "parties", "mps"],
                    "description": "Which page to navigate to",
                },
                "params": {
                    "type": "object",
                    "description": "URL parameters/filters to apply",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Topic filter for votes page (e.g., 'Klima', 'Migration', 'Wohnen')",
                        },
                        "party1": {
                            "type": "string",
                            "description": "First party for comparison on parties page",
                        },
                        "party2": {
                            "type": "string",
                            "description": "Second party for comparison on parties page",
                        },
                        "outcome": {
                            "type": "string",
                            "enum": ["passed", "failed"],
                            "description": "Filter by vote outcome",
                        },
                        "search": {
                            "type": "string",
                            "description": "Search term for MPs page",
                        },
                    },
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of why this view would be helpful (shown to user)",
                },
            },
            "required": ["page", "reason"],
        },
    },
]

async def suggest_navigation(page: str, params: dict | None = None, reason: str = "") -> str:
    """Return a navigation suggestion for the frontend.

    This tool doesn't actually navigate - it returns structured data
    that the frontend can use to show a navigation button.
    """
    return json.dumps({
        "action": "navigate",
        "page": page,
        "params": params or {},
        "reason": reason,
    })


# Map tool names to functions
TOOL_MAP: dict[str, Any] = {
    "get_roll_call_votes": get_roll_call_votes,
    "get_vote_details": get_vote_details,
    "compare_party_votes": compare_party_votes,
    "get_mp_voting_history": get_mp_voting_history,
    "check_party_consistency": check_party_consistency,
    "get_party_alignment_score": get_party_alignment_score,
    "get_absence_rates": get_absence_rates,
    "get_party_unity_scores": get_party_unity_scores,
    "find_rebel_mps": find_rebel_mps,
    "get_mp_info": get_mp_info,
    "search_documents": search_documents,
    "search_procedures": search_procedures,
    "get_plenary_protocols": get_plenary_protocols,
    "get_current_week": get_current_week,
    "get_mp_votes": get_mp_votes,
    "suggest_navigation": suggest_navigation,
}


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str
    content: str


class ChatRequest(BaseModel):
    """Chat request body."""

    messages: list[ChatMessage]
    session_id: str | None = None


async def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool and return the JSON result."""
    if name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool: {name}"})

    try:
        result = await TOOL_MAP[name](**arguments)
        return result  # Already JSON string
    except Exception as e:
        return json.dumps({"error": str(e)})


@router.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, chat_request: ChatRequest):
    """Streaming chat endpoint with tool use.

    Sends messages to Claude, executes tools when requested,
    and streams the response back as Server-Sent Events.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not configured",
        )

    client = anthropic.Anthropic(api_key=api_key)

    # Convert messages to Claude format
    messages = [{"role": m.role, "content": m.content} for m in chat_request.messages]

    async def generate_response():
        """Generator that yields SSE events."""
        nonlocal messages

        try:
            # Initial Claude call
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=CLAUDE_TOOLS,
            )

            # Process response - may need multiple rounds for tool use
            while response.stop_reason == "tool_use":
                # Find tool use blocks
                tool_uses = [
                    block for block in response.content if block.type == "tool_use"
                ]

                # Execute tools
                tool_results = []
                for tool_use in tool_uses:
                    # Notify frontend about tool execution
                    yield f"data: {json.dumps({'type': 'tool_use', 'tool': tool_use.name, 'input': tool_use.input})}\n\n"

                    # Execute the tool
                    result = await execute_tool(tool_use.name, tool_use.input)

                    # Notify frontend about tool result
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_use.name, 'result': json.loads(result)})}\n\n"

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": result,
                        }
                    )

                # Add assistant response and tool results to messages
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

                # Continue conversation with tool results
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                    tools=CLAUDE_TOOLS,
                )

            # Extract final text response
            text_blocks = [
                block for block in response.content if hasattr(block, "text")
            ]
            final_text = "\n".join(block.text for block in text_blocks)

            # Send final text as delta events (for streaming feel)
            # In production, you'd use actual streaming
            yield f"data: {json.dumps({'type': 'text', 'content': final_text})}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except anthropic.APIError as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Internal error: {str(e)}'})}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/simple")
@limiter.limit("10/minute")
async def chat_simple(request: Request, chat_request: ChatRequest):
    """Non-streaming chat endpoint for simpler integration.

    Returns the complete response as JSON instead of SSE stream.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not configured",
        )

    client = anthropic.Anthropic(api_key=api_key)

    # Convert messages to Claude format
    messages = [{"role": m.role, "content": m.content} for m in chat_request.messages]

    try:
        # Initial Claude call
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=CLAUDE_TOOLS,
        )

        tool_calls = []

        # Process response - may need multiple rounds for tool use
        while response.stop_reason == "tool_use":
            tool_uses = [
                block for block in response.content if block.type == "tool_use"
            ]

            tool_results = []
            for tool_use in tool_uses:
                result = await execute_tool(tool_use.name, tool_use.input)
                tool_calls.append(
                    {
                        "tool": tool_use.name,
                        "input": tool_use.input,
                        "result": json.loads(result),
                    }
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    }
                )

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=CLAUDE_TOOLS,
            )

        # Extract final text
        text_blocks = [block for block in response.content if hasattr(block, "text")]
        final_text = "\n".join(block.text for block in text_blocks)

        return {
            "response": final_text,
            "tool_calls": tool_calls,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
