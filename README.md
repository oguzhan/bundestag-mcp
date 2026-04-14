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

### REST API

In addition to the MCP server, the project exposes a FastAPI HTTP layer that serves the same tools over REST. This is useful for web apps, dashboards, or any non-MCP consumer.

Start the API server:

```bash
bundestag-api
```

By default it binds to `http://0.0.0.0:8000`. Configure with environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated CORS origins |
| `ENV` | `development` | Set to `production` to disable auto-reload |

Interactive API docs are available at:

- `http://localhost:8000/docs` — Swagger UI
- `http://localhost:8000/redoc` — ReDoc

Example requests:

```bash
# Health check
curl http://localhost:8000/health

# Recent roll-call votes on a topic
curl "http://localhost:8000/api/v1/votes?topic=Klima&limit=5"

# Party-by-party breakdown of a specific vote
curl http://localhost:8000/api/v1/votes/6391
```

Endpoint groups (see `/docs` for full schemas):

- `GET /api/v1/votes` — list roll-call votes, filter by topic/outcome
- `GET /api/v1/votes/{poll_id}` — party breakdown of a specific vote
- `GET /api/v1/votes/compare` — compare party voting on a topic
- `GET /api/v1/parties/*` — party-level analytics (alignment, unity, absence)
- `GET /api/v1/mps/*` — MP lookup and voting history
- `GET /api/v1/documents/*` — document and procedure search
- `POST /api/chat` — agentic chat endpoint backed by the above tools

## Available Tools

### Document & Procedure Tools

| Tool | Description |
|------|-------------|
| `search_documents` | Search parliamentary documents by keywords, date, type |
| `search_procedures` | Track legislative procedures and their status |
| `get_plenary_protocols` | Access debate transcripts |
| `get_mp_info` | Get MP biographical information |
| `get_current_week` | Get current week's parliamentary schedule |

### Voting Record Tools

| Tool | Description |
|------|-------------|
| `get_roll_call_votes` | List recorded votes with results |
| `get_vote_details` | Party breakdown for a specific vote |
| `compare_party_votes` | Compare party voting on a topic |
| `get_mp_voting_history` | Individual MP's voting record |
| `check_party_consistency` | Analyze party voting patterns on a topic |
| `get_party_alignment_score` | Calculate voting alignment between two parties |
| `get_absence_rates` | Party attendance statistics |
| `get_party_unity_scores` | Internal party voting cohesion |
| `find_rebel_mps` | Find MPs who voted differently from their party |

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
