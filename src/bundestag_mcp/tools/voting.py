"""Voting analysis tools - exposing the gap between rhetoric and action."""

import json
from typing import Any

from ..clients.abgeordnetenwatch import get_abgeordnetenwatch_client
from ..cache.db import get_cache


async def get_roll_call_votes(
    topic: str | None = None,
    limit: int = 10,
) -> str:
    """Get roll-call votes (namentliche Abstimmungen) from the Bundestag.

    These are the votes where every MP's individual vote is recorded.
    Use this to see what was actually voted on and how it passed/failed.

    Args:
        topic: Filter by topic keyword (e.g., 'Migration', 'Klima', 'Rente')
        limit: Maximum number of results

    Returns:
        JSON with roll-call votes including results and party breakdowns
    """
    cache = get_cache()
    cache_params = {"topic": topic, "limit": limit, "type": "roll_call"}

    cached = await cache.get("voting_polls", cache_params)
    if cached is not None:
        return _format_polls_result(cached, from_cache=True)

    client = get_abgeordnetenwatch_client()

    try:
        polls = client.get_polls(topic=topic, limit=limit)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to fetch roll-call votes.",
        }, ensure_ascii=False)

    # Format polls with key info
    formatted = []
    for poll in polls:
        formatted.append({
            "id": poll.get("id"),
            "title": poll.get("label"),
            "date": poll.get("field_poll_date"),
            "passed": poll.get("field_accepted"),
            "topics": [t.get("label") for t in poll.get("field_topics", [])],
            "url": poll.get("abgeordnetenwatch_url"),
            "summary": _clean_html(poll.get("field_intro", ""))[:500],
        })

    await cache.set("voting_polls", cache_params, formatted, ttl_hours=12)

    return _format_polls_result(formatted, from_cache=False)


async def get_vote_details(
    poll_id: int,
) -> str:
    """Get detailed vote breakdown for a specific roll-call vote.

    Shows exactly how each party voted - the "truth" of their position.

    Args:
        poll_id: The poll/vote ID (get from get_roll_call_votes)

    Returns:
        JSON with party-by-party vote breakdown
    """
    cache = get_cache()
    cache_params = {"poll_id": poll_id, "type": "vote_details"}

    cached = await cache.get("vote_details", cache_params)
    if cached is not None:
        return _format_vote_details(cached, poll_id, from_cache=True)

    client = get_abgeordnetenwatch_client()

    try:
        # Get poll info
        poll = client.get_poll_details(poll_id)
        if not poll:
            return json.dumps({"error": f"Poll {poll_id} not found"}, ensure_ascii=False)

        # Get aggregated votes by party
        party_votes = client.aggregate_votes_by_fraction(poll_id)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to fetch vote details.",
        }, ensure_ascii=False)

    result = {
        "poll": {
            "id": poll_id,
            "title": poll.get("label"),
            "date": poll.get("field_poll_date"),
            "passed": poll.get("field_accepted"),
            "summary": _clean_html(poll.get("field_intro", ""))[:800],
        },
        "party_votes": party_votes,
    }

    await cache.set("vote_details", cache_params, [result], ttl_hours=24)

    return _format_vote_details([result], poll_id, from_cache=False)


async def compare_party_votes(
    topic: str,
    limit: int = 5,
) -> str:
    """Compare how different parties voted on a topic.

    This exposes the gap between what parties SAY and how they VOTE.
    Shows voting patterns across multiple votes on the same topic.

    Args:
        topic: Topic to analyze (e.g., 'Migration', 'Klima', 'Soziales')
        limit: Number of recent votes to analyze

    Returns:
        JSON with party voting patterns on the topic
    """
    cache = get_cache()
    cache_params = {"topic": topic, "limit": limit, "type": "party_comparison"}

    cached = await cache.get("party_comparison", cache_params)
    if cached is not None:
        return _format_party_comparison(cached, topic, from_cache=True)

    client = get_abgeordnetenwatch_client()

    try:
        # Get polls on topic
        polls = client.get_polls(topic=topic, limit=limit)

        if not polls:
            return json.dumps({
                "topic": topic,
                "message": f"No roll-call votes found for topic '{topic}'",
                "votes_analyzed": 0,
            }, ensure_ascii=False, indent=2)

        # Aggregate votes across all polls
        party_totals: dict[str, dict[str, int]] = {}
        vote_summaries = []

        for poll in polls:
            poll_id = poll.get("id")
            party_votes = client.aggregate_votes_by_fraction(poll_id)

            vote_summaries.append({
                "title": poll.get("label"),
                "date": poll.get("field_poll_date"),
                "passed": poll.get("field_accepted"),
            })

            for party, votes in party_votes.items():
                if party not in party_totals:
                    party_totals[party] = {"yes": 0, "no": 0, "abstain": 0, "no_show": 0}
                for vote_type, count in votes.items():
                    party_totals[party][vote_type] += count

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to analyze party votes.",
        }, ensure_ascii=False)

    result = {
        "topic": topic,
        "votes_analyzed": len(polls),
        "vote_summaries": vote_summaries,
        "party_totals": party_totals,
    }

    await cache.set("party_comparison", cache_params, [result], ttl_hours=12)

    return _format_party_comparison([result], topic, from_cache=False)


async def get_mp_voting_history(
    name: str,
    topic: str | None = None,
    limit: int = 20,
) -> str:
    """Get detailed voting history for a specific MP.

    Shows exactly how this person voted - not what they said in interviews.

    Args:
        name: MP's name (e.g., 'Merz', 'Scholz', 'Weidel')
        topic: Optional topic filter
        limit: Maximum votes to return

    Returns:
        JSON with MP's voting record
    """
    cache = get_cache()
    cache_params = {"name": name, "topic": topic, "limit": limit, "type": "mp_history"}

    cached = await cache.get("mp_voting_history", cache_params)
    if cached is not None:
        return _format_mp_voting_history(cached, name, from_cache=True)

    client = get_abgeordnetenwatch_client()

    try:
        # Search for politician
        politicians = client.search_politicians(name=name, limit=10)

        if not politicians:
            return json.dumps({
                "error": f"No politician found with name '{name}'",
            }, ensure_ascii=False)

        # Find the one with a current Bundestag mandate
        politician = None
        mandate = None

        for p in politicians:
            m = client.get_mandate_for_politician(p["id"], legislature_period=161)
            if m:
                politician = p
                mandate = m
                break

        if not politician or not mandate:
            # Try previous period
            for p in politicians:
                m = client.get_mandate_for_politician(p["id"], legislature_period=132)
                if m:
                    politician = p
                    mandate = m
                    break

        if not politician or not mandate:
            return json.dumps({
                "error": f"No active Bundestag mandate found for '{name}'",
                "found_politicians": [p.get("label") for p in politicians[:5]],
            }, ensure_ascii=False)

        # Get their votes
        votes = client.get_politician_votes(mandate["id"], limit=limit)

        # Filter by topic if provided
        if topic and votes:
            topic_lower = topic.lower()
            votes = [
                v for v in votes
                if topic_lower in v.get("poll", {}).get("label", "").lower()
            ]

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to fetch MP voting history.",
        }, ensure_ascii=False)

    result = {
        "politician": {
            "id": politician.get("id"),
            "name": politician.get("label"),
            "party": politician.get("party", {}).get("label"),
        },
        "votes": [
            {
                "poll_title": v.get("poll", {}).get("label"),
                "vote": v.get("vote"),
                "url": v.get("poll", {}).get("abgeordnetenwatch_url"),
            }
            for v in votes
        ],
    }

    await cache.set("mp_voting_history", cache_params, [result], ttl_hours=12)

    return _format_mp_voting_history([result], name, from_cache=False)


async def check_party_consistency(
    party: str,
    topic: str,
    limit: int = 10,
) -> str:
    """Check if a party votes consistently with their public statements on a topic.

    This is the key "truth" tool - exposing hypocrisy.

    Args:
        party: Party name (e.g., 'CDU/CSU', 'SPD', 'AfD', 'Grüne')
        topic: Topic to check (e.g., 'Migration', 'Klima')
        limit: Number of votes to analyze

    Returns:
        JSON with consistency analysis
    """
    cache = get_cache()
    cache_params = {"party": party, "topic": topic, "limit": limit, "type": "consistency"}

    cached = await cache.get("party_consistency", cache_params)
    if cached is not None:
        return _format_consistency_result(cached, party, topic, from_cache=True)

    client = get_abgeordnetenwatch_client()

    try:
        polls = client.get_polls(topic=topic, limit=limit)

        if not polls:
            return json.dumps({
                "party": party,
                "topic": topic,
                "message": f"No roll-call votes found for topic '{topic}'",
            }, ensure_ascii=False, indent=2)

        party_lower = party.lower()
        votes_analysis = []

        for poll in polls:
            poll_id = poll.get("id")
            party_votes = client.aggregate_votes_by_fraction(poll_id)

            # Find this party's votes
            party_data = None
            for p_name, p_votes in party_votes.items():
                if party_lower in p_name.lower():
                    party_data = p_votes
                    break

            if party_data:
                total = sum(party_data.values())
                majority_vote = max(party_data, key=party_data.get)

                votes_analysis.append({
                    "title": poll.get("label"),
                    "date": poll.get("field_poll_date"),
                    "passed": poll.get("field_accepted"),
                    "party_voted": majority_vote,
                    "vote_breakdown": party_data,
                    "unity": party_data[majority_vote] / total if total > 0 else 0,
                })

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to analyze party consistency.",
        }, ensure_ascii=False)

    result = {
        "party": party,
        "topic": topic,
        "votes_analyzed": len(votes_analysis),
        "votes": votes_analysis,
    }

    await cache.set("party_consistency", cache_params, [result], ttl_hours=12)

    return _format_consistency_result([result], party, topic, from_cache=False)


def _clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    import re
    clean = re.sub(r'<[^>]+>', '', text)
    clean = clean.replace('&nbsp;', ' ')
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def _format_polls_result(polls: list[dict[str, Any]], from_cache: bool) -> str:
    """Format polls result for LLM consumption."""
    if not polls:
        return json.dumps({
            "count": 0,
            "message": "No roll-call votes found.",
            "polls": [],
        }, ensure_ascii=False, indent=2)

    result = {
        "count": len(polls),
        "cached": from_cache,
        "polls": polls,
    }

    # Create summary
    summary_lines = ["Recent Roll-Call Votes (Namentliche Abstimmungen):", "=" * 50]
    for i, poll in enumerate(polls, 1):
        status = "✓ PASSED" if poll.get("passed") else "✗ REJECTED"
        summary_lines.append(f"\n{i}. {poll.get('title')}")
        summary_lines.append(f"   Date: {poll.get('date')} | {status}")
        if poll.get("topics"):
            summary_lines.append(f"   Topics: {', '.join(poll.get('topics', []))}")

    result["summary"] = "\n".join(summary_lines)

    return json.dumps(result, ensure_ascii=False, indent=2)


def _format_vote_details(data: list[dict[str, Any]], poll_id: int, from_cache: bool) -> str:
    """Format vote details for LLM consumption."""
    if not data:
        return json.dumps({"error": "No data"}, ensure_ascii=False)

    result = data[0]
    result["cached"] = from_cache

    # Create party breakdown summary
    party_votes = result.get("party_votes", {})
    summary_lines = [
        f"Vote Details: {result.get('poll', {}).get('title')}",
        "=" * 50,
        f"Date: {result.get('poll', {}).get('date')}",
        f"Result: {'PASSED' if result.get('poll', {}).get('passed') else 'REJECTED'}",
        "",
        "PARTY BREAKDOWN:",
        "-" * 30,
    ]

    for party, votes in sorted(party_votes.items()):
        total = sum(votes.values())
        yes_pct = (votes.get("yes", 0) / total * 100) if total > 0 else 0
        no_pct = (votes.get("no", 0) / total * 100) if total > 0 else 0

        summary_lines.append(f"\n{party}:")
        summary_lines.append(f"  YES: {votes.get('yes', 0)} ({yes_pct:.0f}%)")
        summary_lines.append(f"  NO:  {votes.get('no', 0)} ({no_pct:.0f}%)")
        if votes.get("abstain", 0) > 0:
            summary_lines.append(f"  ABSTAIN: {votes.get('abstain', 0)}")
        if votes.get("no_show", 0) > 0:
            summary_lines.append(f"  ABSENT: {votes.get('no_show', 0)}")

    result["summary"] = "\n".join(summary_lines)

    return json.dumps(result, ensure_ascii=False, indent=2)


def _format_party_comparison(data: list[dict[str, Any]], topic: str, from_cache: bool) -> str:
    """Format party comparison for LLM consumption."""
    if not data:
        return json.dumps({"error": "No data"}, ensure_ascii=False)

    result = data[0]
    result["cached"] = from_cache

    party_totals = result.get("party_totals", {})
    summary_lines = [
        f"Party Voting Patterns on '{topic}'",
        "=" * 50,
        f"Votes analyzed: {result.get('votes_analyzed', 0)}",
        "",
        "AGGREGATED PARTY POSITIONS:",
        "-" * 30,
    ]

    for party, totals in sorted(party_totals.items()):
        total_votes = sum(totals.values())
        if total_votes == 0:
            continue

        yes_pct = totals.get("yes", 0) / total_votes * 100
        no_pct = totals.get("no", 0) / total_votes * 100

        # Determine overall stance
        if yes_pct > 70:
            stance = "STRONGLY SUPPORTS"
        elif yes_pct > 50:
            stance = "LEANS SUPPORT"
        elif no_pct > 70:
            stance = "STRONGLY OPPOSES"
        elif no_pct > 50:
            stance = "LEANS OPPOSE"
        else:
            stance = "MIXED/SPLIT"

        summary_lines.append(f"\n{party}: {stance}")
        summary_lines.append(f"  YES: {totals.get('yes', 0)} | NO: {totals.get('no', 0)} | Abstain: {totals.get('abstain', 0)}")

    result["summary"] = "\n".join(summary_lines)

    return json.dumps(result, ensure_ascii=False, indent=2)


def _format_mp_voting_history(data: list[dict[str, Any]], name: str, from_cache: bool) -> str:
    """Format MP voting history for LLM consumption."""
    if not data:
        return json.dumps({"error": "No data"}, ensure_ascii=False)

    result = data[0]
    result["cached"] = from_cache

    politician = result.get("politician", {})
    votes = result.get("votes", [])

    summary_lines = [
        f"Voting Record: {politician.get('name')} ({politician.get('party')})",
        "=" * 50,
        f"Votes shown: {len(votes)}",
        "",
    ]

    for v in votes:
        vote_symbol = {"yes": "✓ YES", "no": "✗ NO", "abstain": "○ ABSTAIN", "no_show": "- ABSENT"}.get(
            v.get("vote"), v.get("vote")
        )
        summary_lines.append(f"{vote_symbol}: {v.get('poll_title')}")

    result["summary"] = "\n".join(summary_lines)

    return json.dumps(result, ensure_ascii=False, indent=2)


def _format_consistency_result(
    data: list[dict[str, Any]],
    party: str,
    topic: str,
    from_cache: bool,
) -> str:
    """Format consistency analysis for LLM consumption."""
    if not data:
        return json.dumps({"error": "No data"}, ensure_ascii=False)

    result = data[0]
    result["cached"] = from_cache

    votes = result.get("votes", [])
    summary_lines = [
        f"Consistency Check: {party} on '{topic}'",
        "=" * 50,
        f"Votes analyzed: {len(votes)}",
        "",
        "VOTE-BY-VOTE ANALYSIS:",
        "-" * 30,
    ]

    yes_count = sum(1 for v in votes if v.get("party_voted") == "yes")
    no_count = sum(1 for v in votes if v.get("party_voted") == "no")

    for v in votes:
        unity_pct = v.get("unity", 0) * 100
        unity_label = "UNIFIED" if unity_pct > 90 else "SPLIT" if unity_pct < 70 else "MOSTLY UNIFIED"

        summary_lines.append(f"\n• {v.get('title')[:60]}...")
        summary_lines.append(f"  {party} voted: {v.get('party_voted').upper()} ({unity_label}, {unity_pct:.0f}% agreement)")
        summary_lines.append(f"  Bill {'PASSED' if v.get('passed') else 'REJECTED'}")

    summary_lines.append("")
    summary_lines.append(f"OVERALL: {party} voted YES on {yes_count}/{len(votes)} bills, NO on {no_count}/{len(votes)}")

    result["summary"] = "\n".join(summary_lines)

    return json.dumps(result, ensure_ascii=False, indent=2)


# =============================================================================
# ADVANCED ANALYTICAL TOOLS
# These answer questions that web search cannot
# =============================================================================


async def get_party_alignment_score(
    party1: str,
    party2: str,
    limit: int = 20,
) -> str:
    """Calculate how often two parties vote the same way.

    This answers: "How often do CDU and AfD vote together?"
    Web search cannot compute this - it requires aggregating across all votes.

    Args:
        party1: First party (e.g., 'CDU/CSU', 'SPD')
        party2: Second party (e.g., 'AfD', 'Grüne')
        limit: Number of recent votes to analyze

    Returns:
        JSON with alignment percentage and breakdown
    """
    cache = get_cache()
    cache_params = {"party1": party1, "party2": party2, "limit": limit, "type": "alignment"}

    cached = await cache.get("party_alignment", cache_params)
    if cached is not None:
        return json.dumps(cached[0], ensure_ascii=False, indent=2)

    client = get_abgeordnetenwatch_client()

    try:
        polls = client.get_polls(limit=limit)

        if not polls:
            return json.dumps({
                "error": "No polls found",
            }, ensure_ascii=False)

        party1_lower = party1.lower()
        party2_lower = party2.lower()

        same_vote = 0
        different_vote = 0
        vote_details = []

        for poll in polls:
            poll_id = poll.get("id")
            party_votes = client.aggregate_votes_by_fraction(poll_id)

            # Find each party's majority vote
            p1_vote = None
            p2_vote = None

            for p_name, p_votes in party_votes.items():
                p_name_lower = p_name.lower()
                total = sum(p_votes.values())
                if total == 0:
                    continue
                majority = max(p_votes, key=p_votes.get)

                if party1_lower in p_name_lower:
                    p1_vote = majority
                elif party2_lower in p_name_lower:
                    p2_vote = majority

            if p1_vote and p2_vote:
                aligned = p1_vote == p2_vote
                if aligned:
                    same_vote += 1
                else:
                    different_vote += 1

                vote_details.append({
                    "title": poll.get("label")[:60],
                    "date": poll.get("field_poll_date"),
                    party1: p1_vote,
                    party2: p2_vote,
                    "aligned": aligned,
                })

        total_compared = same_vote + different_vote
        alignment_pct = (same_vote / total_compared * 100) if total_compared > 0 else 0

        result = {
            "party1": party1,
            "party2": party2,
            "votes_analyzed": total_compared,
            "alignment_percentage": round(alignment_pct, 1),
            "same_vote_count": same_vote,
            "different_vote_count": different_vote,
            "interpretation": _interpret_alignment(alignment_pct),
            "vote_details": vote_details,
            "summary": f"{party1} and {party2} voted the same way on {same_vote}/{total_compared} votes ({alignment_pct:.1f}% alignment)",
        }

        await cache.set("party_alignment", cache_params, [result], ttl_hours=12)

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to calculate party alignment.",
        }, ensure_ascii=False)


async def get_absence_rates(
    limit: int = 20,
) -> str:
    """Calculate absence (no-show) rates for each party.

    This answers: "Which party skips the most votes?"
    Requires aggregating no-show data across all votes.

    Args:
        limit: Number of recent votes to analyze

    Returns:
        JSON with absence rates per party
    """
    cache = get_cache()
    cache_params = {"limit": limit, "type": "absence_rates"}

    cached = await cache.get("absence_rates", cache_params)
    if cached is not None:
        return json.dumps(cached[0], ensure_ascii=False, indent=2)

    client = get_abgeordnetenwatch_client()

    try:
        polls = client.get_polls(limit=limit)

        if not polls:
            return json.dumps({"error": "No polls found"}, ensure_ascii=False)

        # Aggregate totals per party
        party_stats: dict[str, dict[str, int]] = {}

        for poll in polls:
            poll_id = poll.get("id")
            party_votes = client.aggregate_votes_by_fraction(poll_id)

            for p_name, p_votes in party_votes.items():
                # Clean party name
                clean_name = p_name.split(" (")[0] if " (" in p_name else p_name

                if clean_name not in party_stats:
                    party_stats[clean_name] = {"total_votes": 0, "no_show": 0}

                party_stats[clean_name]["total_votes"] += sum(p_votes.values())
                party_stats[clean_name]["no_show"] += p_votes.get("no_show", 0)

        # Calculate percentages
        absence_rates = []
        for party, stats in party_stats.items():
            if stats["total_votes"] > 0:
                rate = stats["no_show"] / stats["total_votes"] * 100
                absence_rates.append({
                    "party": party,
                    "absence_rate": round(rate, 1),
                    "absent_votes": stats["no_show"],
                    "total_possible": stats["total_votes"],
                })

        # Sort by absence rate descending
        absence_rates.sort(key=lambda x: x["absence_rate"], reverse=True)

        result = {
            "votes_analyzed": len(polls),
            "party_absence_rates": absence_rates,
            "summary": _format_absence_summary(absence_rates),
        }

        await cache.set("absence_rates", cache_params, [result], ttl_hours=12)

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to calculate absence rates.",
        }, ensure_ascii=False)


async def get_party_unity_scores(
    limit: int = 20,
) -> str:
    """Calculate how unified each party votes (internal agreement).

    This answers: "Which party is most unified in their voting?"
    Requires calculating what % of each party votes with their majority.

    Args:
        limit: Number of recent votes to analyze

    Returns:
        JSON with unity scores per party
    """
    cache = get_cache()
    cache_params = {"limit": limit, "type": "unity_scores"}

    cached = await cache.get("unity_scores", cache_params)
    if cached is not None:
        return json.dumps(cached[0], ensure_ascii=False, indent=2)

    client = get_abgeordnetenwatch_client()

    try:
        polls = client.get_polls(limit=limit)

        if not polls:
            return json.dumps({"error": "No polls found"}, ensure_ascii=False)

        # Track unity per party per vote
        party_unity: dict[str, list[float]] = {}

        for poll in polls:
            poll_id = poll.get("id")
            party_votes = client.aggregate_votes_by_fraction(poll_id)

            for p_name, p_votes in party_votes.items():
                clean_name = p_name.split(" (")[0] if " (" in p_name else p_name

                # Calculate unity for this vote (% voting with majority)
                total = sum(p_votes.values())
                if total == 0:
                    continue

                # Exclude no-shows from unity calculation
                voting_total = total - p_votes.get("no_show", 0)
                if voting_total == 0:
                    continue

                majority_count = max(
                    p_votes.get("yes", 0),
                    p_votes.get("no", 0),
                    p_votes.get("abstain", 0)
                )
                unity = majority_count / voting_total

                if clean_name not in party_unity:
                    party_unity[clean_name] = []
                party_unity[clean_name].append(unity)

        # Calculate average unity
        unity_scores = []
        for party, scores in party_unity.items():
            if scores:
                avg_unity = sum(scores) / len(scores) * 100
                unity_scores.append({
                    "party": party,
                    "unity_score": round(avg_unity, 1),
                    "votes_analyzed": len(scores),
                    "interpretation": "Very unified" if avg_unity > 95 else "Unified" if avg_unity > 85 else "Somewhat split" if avg_unity > 70 else "Often divided",
                })

        # Sort by unity score descending
        unity_scores.sort(key=lambda x: x["unity_score"], reverse=True)

        result = {
            "votes_analyzed": len(polls),
            "party_unity_scores": unity_scores,
            "summary": _format_unity_summary(unity_scores),
        }

        await cache.set("unity_scores", cache_params, [result], ttl_hours=12)

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to calculate unity scores.",
        }, ensure_ascii=False)


async def find_rebel_mps(
    party: str,
    limit: int = 10,
) -> str:
    """Find MPs who voted against their own party most often.

    This answers: "Which CDU MPs vote against their party?"
    Requires comparing each MP's vote to their party's majority.

    Args:
        party: Party to analyze (e.g., 'CDU/CSU', 'SPD')
        limit: Number of recent votes to analyze

    Returns:
        JSON with list of rebel MPs and their dissenting votes
    """
    cache = get_cache()
    cache_params = {"party": party, "limit": limit, "type": "rebel_mps"}

    cached = await cache.get("rebel_mps", cache_params)
    if cached is not None:
        return json.dumps(cached[0], ensure_ascii=False, indent=2)

    client = get_abgeordnetenwatch_client()
    party_lower = party.lower()

    try:
        polls = client.get_polls(limit=limit)

        if not polls:
            return json.dumps({"error": "No polls found"}, ensure_ascii=False)

        # Track dissent per MP
        mp_dissent: dict[str, dict[str, Any]] = {}

        for poll in polls:
            poll_id = poll.get("id")

            # Get party's majority vote
            party_votes = client.aggregate_votes_by_fraction(poll_id)
            party_majority = None

            for p_name, p_votes in party_votes.items():
                if party_lower in p_name.lower():
                    voting_total = sum(p_votes.values()) - p_votes.get("no_show", 0)
                    if voting_total > 0:
                        party_majority = max(
                            [("yes", p_votes.get("yes", 0)),
                             ("no", p_votes.get("no", 0)),
                             ("abstain", p_votes.get("abstain", 0))],
                            key=lambda x: x[1]
                        )[0]
                    break

            if not party_majority:
                continue

            # Get individual votes and find dissenters
            votes = client.get_votes_for_poll(poll_id)

            for vote in votes:
                fraction = vote.get("fraction", {})
                fraction_name = fraction.get("label", "")

                if party_lower not in fraction_name.lower():
                    continue

                mp_vote = vote.get("vote")
                if mp_vote == "no_show":
                    continue  # Don't count absences as dissent

                mandate = vote.get("mandate", {})
                mp_name = mandate.get("label", "Unknown")
                # Clean MP name (remove period info)
                if " (" in mp_name:
                    mp_name = mp_name.split(" (")[0]

                if mp_name not in mp_dissent:
                    mp_dissent[mp_name] = {
                        "name": mp_name,
                        "total_votes": 0,
                        "dissenting_votes": 0,
                        "dissent_examples": [],
                    }

                mp_dissent[mp_name]["total_votes"] += 1

                if mp_vote != party_majority:
                    mp_dissent[mp_name]["dissenting_votes"] += 1
                    if len(mp_dissent[mp_name]["dissent_examples"]) < 3:
                        mp_dissent[mp_name]["dissent_examples"].append({
                            "poll": poll.get("label")[:50],
                            "party_voted": party_majority,
                            "mp_voted": mp_vote,
                        })

        # Calculate dissent rates and filter
        rebels = []
        for mp_name, data in mp_dissent.items():
            if data["total_votes"] > 0 and data["dissenting_votes"] > 0:
                rate = data["dissenting_votes"] / data["total_votes"] * 100
                rebels.append({
                    "name": data["name"],
                    "dissent_rate": round(rate, 1),
                    "dissenting_votes": data["dissenting_votes"],
                    "total_votes": data["total_votes"],
                    "examples": data["dissent_examples"],
                })

        # Sort by dissent rate descending
        rebels.sort(key=lambda x: x["dissent_rate"], reverse=True)

        result = {
            "party": party,
            "votes_analyzed": len(polls),
            "rebels_found": len(rebels),
            "rebel_mps": rebels[:20],  # Top 20 rebels
            "summary": _format_rebel_summary(party, rebels[:10]),
        }

        await cache.set("rebel_mps", cache_params, [result], ttl_hours=12)

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to find rebel MPs.",
        }, ensure_ascii=False)


def _interpret_alignment(pct: float) -> str:
    """Interpret alignment percentage."""
    if pct >= 90:
        return "Near-identical voting (>90%)"
    elif pct >= 75:
        return "High alignment (75-90%)"
    elif pct >= 50:
        return "Moderate alignment (50-75%)"
    elif pct >= 25:
        return "Low alignment (25-50%)"
    else:
        return "Opposing positions (<25%)"


def _format_absence_summary(rates: list[dict[str, Any]]) -> str:
    """Format absence rates summary."""
    lines = ["PARTY ABSENCE RATES", "=" * 40, ""]
    for r in rates:
        lines.append(f"{r['party']}: {r['absence_rate']}% absent ({r['absent_votes']}/{r['total_possible']} votes)")
    return "\n".join(lines)


def _format_unity_summary(scores: list[dict[str, Any]]) -> str:
    """Format unity scores summary."""
    lines = ["PARTY UNITY SCORES (% voting with majority)", "=" * 40, ""]
    for s in scores:
        lines.append(f"{s['party']}: {s['unity_score']}% - {s['interpretation']}")
    return "\n".join(lines)


def _format_rebel_summary(party: str, rebels: list[dict[str, Any]]) -> str:
    """Format rebel MPs summary."""
    if not rebels:
        return f"No dissenting MPs found in {party}"

    lines = [f"TOP DISSENTERS IN {party.upper()}", "=" * 40, ""]
    for r in rebels:
        lines.append(f"{r['name']}: {r['dissent_rate']}% dissent ({r['dissenting_votes']}/{r['total_votes']} votes)")
    return "\n".join(lines)
