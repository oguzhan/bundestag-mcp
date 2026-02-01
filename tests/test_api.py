"""Tests for the FastAPI endpoints."""

import pytest
import httpx
from bundestag_mcp.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    from starlette.testclient import TestClient
    # Use transport-based approach for newer httpx
    transport = httpx.ASGITransport(app=app)
    with httpx.Client(transport=transport, base_url="http://test") as client:
        yield client


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "Bundestag Truth API"

    def test_health(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestVotesEndpoints:
    """Test vote-related endpoints."""

    def test_list_votes(self, client):
        """Test listing votes."""
        response = client.get("/api/v1/votes?limit=3")
        assert response.status_code == 200
        data = response.json()
        # Should return either polls list or error structure
        assert isinstance(data, dict)

    def test_list_votes_with_topic(self, client):
        """Test listing votes filtered by topic."""
        response = client.get("/api/v1/votes?topic=Klima&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestPartiesEndpoints:
    """Test party-related endpoints."""

    def test_party_unity(self, client):
        """Test party unity scores endpoint."""
        response = client.get("/api/v1/parties/unity?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_party_absence(self, client):
        """Test party absence rates endpoint."""
        response = client.get("/api/v1/parties/absence?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestMPsEndpoints:
    """Test MP-related endpoints."""

    def test_get_mp_info(self, client):
        """Test getting MP info."""
        response = client.get("/api/v1/mps/Scholz")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestDocumentsEndpoints:
    """Test document-related endpoints."""

    def test_search_documents(self, client):
        """Test document search."""
        response = client.get("/api/v1/documents?keywords=Klimaschutz&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_get_calendar(self, client):
        """Test calendar endpoint."""
        response = client.get("/api/v1/calendar/week")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestChatEndpoint:
    """Test chat endpoint (without API key)."""

    def test_chat_requires_api_key(self, client):
        """Test that chat endpoint requires API key."""
        response = client.post(
            "/api/chat/simple",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        # Should fail without ANTHROPIC_API_KEY
        assert response.status_code == 500
        assert "ANTHROPIC_API_KEY" in response.json()["detail"]
