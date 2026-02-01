# MCP vs Web Search: Unique Value Proposition

This document defines what questions the Bundestag MCP can answer that web search cannot. Use this as a test reference to validate the MCP's value.

## The Core Difference

| Capability | Web Search | Bundestag MCP |
|------------|------------|---------------|
| Find a single vote result | ✅ | ✅ |
| Find an MP's profile | ✅ | ✅ |
| Aggregate across multiple votes | ❌ | ✅ |
| Calculate voting statistics | ❌ | ✅ |
| Compare patterns over time | ❌ | ✅ |
| Cross-reference MPs and bills | ❌ | ✅ |
| Detect inconsistencies | ❌ | ✅ |

## Test Questions: MCP Should Answer, Web Search Cannot

### Category 1: Cross-Party Alignment Analysis

| Question | Why Web Search Fails | Expected MCP Output |
|----------|---------------------|---------------------|
| "How often do CDU/CSU and AfD vote the same way?" | Requires aggregating all votes and comparing | Percentage score (e.g., "78% alignment on 39 votes") |
| "Which two parties vote together most often?" | Requires pairwise comparison of all parties | Ranked list of party pairs with alignment % |
| "On which votes was the governing coalition split?" | Requires identifying coalition + checking each vote | List of specific votes with breakdown |
| "Show me votes where all parties agreed" | Requires checking unanimity across all votes | List of unanimous votes |

### Category 2: Individual MP Analysis

| Question | Why Web Search Fails | Expected MCP Output |
|----------|---------------------|---------------------|
| "Which MPs voted against their own party most often?" | Requires comparing each MP's vote to party majority | Ranked list of "rebel" MPs with count |
| "How many votes did [MP] miss?" | Requires counting no-shows across all votes | Absence count and percentage |
| "Did [MP] vote consistently on [topic]?" | Requires filtering votes by topic + checking consistency | Consistency score with list of votes |
| "Compare voting records of [MP1] vs [MP2]" | Requires pairwise comparison across all shared votes | Agreement percentage + differing votes |

### Category 3: Party Consistency (Say vs Do)

| Question | Why Web Search Fails | Expected MCP Output |
|----------|---------------------|---------------------|
| "Does AfD vote with the 'establishment' they criticize?" | Requires defining establishment + calculating alignment | Alignment % with CDU/SPD |
| "Did Grüne vote YES on all climate-related bills?" | Requires topic filtering + consistency check | List of climate votes with Grüne position |
| "Which party has the highest no-show rate?" | Requires calculating absence % per party | Ranked parties by absence rate |
| "Which party is most 'unified' in their voting?" | Requires calculating internal agreement per party | Ranked parties by unity score |

### Category 4: Temporal Analysis

| Question | Why Web Search Fails | Expected MCP Output |
|----------|---------------------|---------------------|
| "How did [party] voting change after the election?" | Requires comparing periods | Before/after comparison |
| "Are parties becoming more polarized over time?" | Requires trend analysis | Polarization trend data |
| "When did [party] start voting differently on [topic]?" | Requires temporal pattern detection | Date/period of shift |

### Category 5: Structural/Statistical Queries

| Question | Why Web Search Fails | Expected MCP Output |
|----------|---------------------|---------------------|
| "List all MPs who voted NO on [specific bill]" | Single page might show this, but not exportable | Structured list with party affiliation |
| "Find votes that passed with less than 60% support" | Requires calculating % for each vote | List of close votes |
| "Which topics have the most cross-party disagreement?" | Requires analyzing votes by topic | Ranked topics by disagreement |
| "Export voting data for [party] as CSV" | Web shows HTML, not exportable | Structured data export |

## Validation Criteria

For each question above, the MCP passes the test if:

1. **Accuracy**: The answer matches official records
2. **Completeness**: All relevant data is included (not just samples)
3. **Speed**: Answer returned in <30 seconds
4. **Structure**: Output is structured (JSON) not prose
5. **Reproducibility**: Same question → same answer

## Tools Required

To answer all questions above, the MCP needs:

### Currently Implemented ✅
- `get_roll_call_votes` - List recorded votes
- `get_vote_details` - Party breakdown per vote
- `compare_party_votes` - Aggregate party positions on topic
- `get_mp_voting_history` - Individual MP votes
- `check_party_consistency` - Party consistency on topic

### To Be Implemented 🔨
- `get_party_alignment_score` - Pairwise party agreement %
- `find_rebel_mps` - MPs voting against their party
- `get_absence_rates` - No-show statistics
- `compare_mps` - Head-to-head MP comparison
- `get_party_unity_scores` - Internal party agreement
- `find_close_votes` - Votes with narrow margins
- `get_unanimous_votes` - Votes with full agreement

## Success Metric

The MCP is successful when a user can ask any question from the tables above and receive an accurate, structured answer within 30 seconds - something impossible with web search alone.
