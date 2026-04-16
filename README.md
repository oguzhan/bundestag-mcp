# Bundestag MCP Server

> **⚠️ Work in Progress**: This project is under active development. APIs may change. Contributions welcome!

An MCP (Model Context Protocol) server that provides programmatic access to official German Bundestag parliamentary data. This enables LLMs to answer questions about German parliament activities, legislation, voting records, and members.

## Disclaimer

**This project is strictly non-partisan and has no political intentions.**

The sole purpose is to provide transparent, programmatic access to **publicly available official data** from the German parliament. All data comes from official government sources and independent transparency organizations. This tool:

- Does **not** interpret, editorialize, or present any political opinions
- Does **not** favor or oppose any political party
- Simply provides factual access to public parliamentary records
- Is intended for civic engagement, journalism, research, and education

The authors are not responsible for how this data is used or interpreted.

## Data Sources

All data is retrieved from official, publicly available sources:

| Source | Organization | Data Provided | License |
|--------|--------------|---------------|---------|
| **[DIP API](https://dip.bundestag.de/)** | Deutscher Bundestag (Official) | Parliamentary documents, legislative procedures, plenary protocols, MP information | Public government data |
| **[AbgeordnetenWatch API](https://www.abgeordnetenwatch.de/api)** | AbgeordnetenWatch e.V. (Independent) | Roll-call votes, individual MP voting records | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### About the Data Sources

- **DIP (Dokumentations- und Informationssystem für Parlamentsmaterialien)**: The official documentation system of the German Bundestag. All parliamentary documents, procedures, and protocols are public records.

- **AbgeordnetenWatch**: An independent, non-partisan transparency organization that documents how elected representatives vote. Their data is published under CC0 (public domain) license.

Both sources provide factual records of parliamentary proceedings without editorial content.

## Features

### Core Tools (DIP API)
- **Search Documents**: Find parliamentary documents (Drucksachen) including bills, motions, and interpellations
- **Track Legislation**: Follow legislative procedures (Vorgänge) and their current status
- **Access Debates**: Search plenary protocol transcripts (Plenarprotokolle)
- **MP Information**: Look up members of parliament, their party, constituency, and roles
- **Weekly Schedule**: Get the current week's Bundestag activities

### Voting Record Tools (AbgeordnetenWatch API)
- **Roll-Call Votes**: Access official recorded votes (namentliche Abstimmungen)
- **Vote Details**: See party-by-party breakdown of specific votes
- **Party Comparison**: Compare voting patterns across parties on any topic
- **MP Voting History**: Access individual MP voting records
- **Party Alignment**: Calculate voting alignment between parties
- **Absence Rates**: View attendance statistics
- **Party Unity**: Measure internal party voting cohesion

## Installation

### Prerequisites

- Python 3.11 or higher
- pip or uv package manager

### Install from source

```bash
# Clone the repository
git clone https://github.com/oguzhan/bundestag-mcp.git
cd bundestag-mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

## Usage

### With Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "bundestag": {
      "command": "python",
      "args": ["-m", "bundestag_mcp.server"],
      "cwd": "/path/to/bundestag-mcp"
    }
  }
}
```

### Running Standalone

```bash
python -m bundestag_mcp.server
```

## Available Tools

The server exposes 15 tools across three groups. Each entry documents its full input schema. Required parameters are marked ✓; optional ones show the default in parentheses.

### Document & Procedure Tools (DIP API)

#### `search_documents`
Search parliamentary documents (Drucksachen): bills, motions, reports, and answers to parliamentary questions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keywords` | string | ✓ | Search keywords, German or English (e.g. `"Klimaschutz"` or `"climate protection"`) |
| `date_start` | string | — | Start date, `YYYY-MM-DD` |
| `date_end` | string | — | End date, `YYYY-MM-DD` |
| `document_type` | string | — | `"Gesetzentwurf"` (bill), `"Antrag"` (motion), `"Kleine Anfrage"` (minor interpellation), `"Große Anfrage"` (major interpellation) |
| `limit` | integer | — (10) | Max results, up to 50 |

#### `search_procedures`
Track legislative processes (Vorgänge) and their current status.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keywords` | string | ✓ | Search keywords for the procedure title or content |
| `status` | string | — | One of `"Noch nicht beraten"`, `"Im Bundestag noch nicht beraten"`, `"Überwiesen"`, `"Beschlussempfehlung liegt vor"`, `"Abgeschlossen"` |
| `date_start` | string | — | Start date, `YYYY-MM-DD` |
| `date_end` | string | — | End date, `YYYY-MM-DD` |
| `limit` | integer | — (10) | Max results |

#### `get_plenary_protocols`
Search plenary debate transcripts (Plenarprotokolle) by keyword or speaker.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keywords` | string | — | Search keywords to find in debate transcripts |
| `speaker` | string | — | Filter by speaker name |
| `date_start` | string | — | Start date, `YYYY-MM-DD` |
| `date_end` | string | — | End date, `YYYY-MM-DD` |
| `limit` | integer | — (10) | Max results |

#### `get_mp_info`
Look up an MdB's party affiliation, constituency, committee memberships, and biographical info.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | — | MP name, full or partial (e.g. `"Scholz"` or `"Olaf Scholz"`) |
| `mp_id` | string | — | Bundestag person ID, if known |

At least one of `name` or `mp_id` should be provided.

#### `get_mp_votes`
Voting record for a single MP, optionally filtered by topic or date range.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mp_id` | string | — | Bundestag person ID |
| `name` | string | — | MP name (alternative to `mp_id`) |
| `topic_filter` | string | — | Filter votes by topic keywords |
| `date_start` | string | — | Start date, `YYYY-MM-DD` |
| `date_end` | string | — | End date, `YYYY-MM-DD` |
| `limit` | integer | — (10) | Max results |

At least one of `mp_id` or `name` should be provided.

#### `get_current_week`
The current week's Bundestag schedule: plenary debates, votes, committee meetings. Takes no parameters.

### Voting Record Tools (AbgeordnetenWatch API)

#### `get_roll_call_votes`
List roll-call votes (namentliche Abstimmungen) where each MP's vote is recorded. Foundation for the other voting tools.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `topic` | string | — | Filter by topic keyword (e.g. `"Migration"`, `"Klima"`, `"Rente"`, `"Wohnen"`) |
| `limit` | integer | — (10) | Max results |

#### `get_vote_details`
Party-by-party breakdown for one specific vote.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `poll_id` | integer | ✓ | Poll/vote ID (obtain from `get_roll_call_votes`) |

#### `compare_party_votes`
Compare how different parties voted on a topic across multiple recent votes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `topic` | string | ✓ | Topic to analyze (e.g. `"Migration"`, `"Klima"`, `"Soziales"`, `"Rente"`) |
| `limit` | integer | — (5) | Number of recent votes to analyze |

#### `get_mp_voting_history`
Detailed voting history for one MP — how they actually voted, not what they said.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | ✓ | MP name (e.g. `"Merz"`, `"Scholz"`, `"Weidel"`, `"Habeck"`) |
| `topic` | string | — | Optional topic filter |
| `limit` | integer | — (20) | Max votes to return |

#### `check_party_consistency`
Check whether a party votes consistently on a given topic.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `party` | string | ✓ | Party name (`"CDU/CSU"`, `"SPD"`, `"AfD"`, `"Grüne"`, `"Die Linke"`, `"BSW"`) |
| `topic` | string | ✓ | Topic to check (e.g. `"Migration"`, `"Klima"`, `"Rente"`) |
| `limit` | integer | — (10) | Number of votes to analyze |

### Advanced Analytical Tools

These compute across multiple votes — answers that web search cannot produce.

#### `get_party_alignment_score`
How often two parties vote the same way.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `party1` | string | ✓ | First party |
| `party2` | string | ✓ | Second party |
| `limit` | integer | — (20) | Number of votes to analyze |

#### `get_absence_rates`
Per-party no-show rates across recorded votes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | — (20) | Number of votes to analyze |

#### `get_party_unity_scores`
Percentage of each party that votes with its own majority — internal cohesion.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | — (20) | Number of votes to analyze |

#### `find_rebel_mps`
MPs who most often vote against their own party.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `party` | string | ✓ | Party to analyze |
| `limit` | integer | — (10) | Number of votes to analyze |

## Example Queries

```
"What documents about renewable energy were published this month?"
"What is the current status of the housing reform bill?"
"Show me the voting breakdown for the recent tax legislation"
"How often do the coalition parties vote together?"
"What is the attendance rate for each party?"
```

## Caching

The server caches API responses locally (`~/.bundestag_mcp/cache.db`) to:
- Improve response times
- Reduce load on public APIs
- Enable offline access to previously fetched data

Cache duration: 4-24 hours depending on data type.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

### Tests

The project includes unit tests and validation tests for the voting analysis:

```bash
# Run all tests
pytest

# Run voting calculation tests with verbose output
pytest tests/test_voting*.py -v
```

Key test coverage:
- **Alignment calculation**: Tests for 0%, 50%, 100% alignment scenarios
- **Real data validation**: Tests using actual Poll 6391 data to verify calculations
- **Edge cases**: Missing parties, abstention handling, interpretation text

## License

MIT License - see [LICENSE](LICENSE) file.

## Contributing

Contributions are welcome. Please ensure any changes maintain the non-partisan nature of this project.

## Acknowledgments

- [Deutscher Bundestag](https://www.bundestag.de/) for providing public access to parliamentary data
- [AbgeordnetenWatch e.V.](https://www.abgeordnetenwatch.de/) for their transparency work and open API
- [bundestag-api](https://pypi.org/project/bundestag-api/) Python package maintainers
