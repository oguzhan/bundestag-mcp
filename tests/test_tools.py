"""Tests for MCP tools."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from bundestag_mcp.tools.documents import search_documents
from bundestag_mcp.tools.members import get_mp_info
from bundestag_mcp.tools.procedures import search_procedures
from bundestag_mcp.tools.calendar import get_current_week


@pytest.fixture
def mock_cache():
    """Create a mock cache that always returns None (cache miss)."""
    with patch("bundestag_mcp.tools.documents.get_cache") as mock:
        cache = AsyncMock()
        cache.get.return_value = None
        cache.set.return_value = None
        mock.return_value = cache
        yield cache


@pytest.fixture
def mock_dip_client():
    """Create a mock DIP client."""
    with patch("bundestag_mcp.tools.documents.get_dip_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


class TestSearchDocuments:
    """Tests for search_documents tool."""

    @pytest.mark.asyncio
    async def test_search_documents_basic(self, mock_cache, mock_dip_client):
        """Test basic document search."""
        mock_dip_client.search_documents.return_value = [
            {
                "id": "123",
                "titel": "Klimaschutzgesetz",
                "dokumentart": "Gesetzentwurf",
                "datum": "2024-01-15",
            }
        ]

        result = await search_documents(keywords="Klima")
        data = json.loads(result)

        assert data["count"] == 1
        assert len(data["documents"]) == 1
        mock_dip_client.search_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_documents_no_results(self, mock_cache, mock_dip_client):
        """Test document search with no results."""
        mock_dip_client.search_documents.return_value = []

        result = await search_documents(keywords="nonexistent12345")
        data = json.loads(result)

        assert data["count"] == 0
        assert "No documents found" in data["message"]


class TestGetMpInfo:
    """Tests for get_mp_info tool."""

    @pytest.mark.asyncio
    async def test_get_mp_info_no_params(self):
        """Test get_mp_info without parameters."""
        result = await get_mp_info()
        data = json.loads(result)

        assert "error" in data
        assert "provide either" in data["error"].lower()


class TestSearchProcedures:
    """Tests for search_procedures tool."""

    @pytest.mark.asyncio
    async def test_search_procedures_basic(self):
        """Test basic procedure search structure."""
        with patch("bundestag_mcp.tools.procedures.get_cache") as cache_mock:
            cache = AsyncMock()
            cache.get.return_value = None
            cache.set.return_value = None
            cache_mock.return_value = cache

            with patch("bundestag_mcp.tools.procedures.get_dip_client") as client_mock:
                client = MagicMock()
                client.search_procedures.return_value = []
                client_mock.return_value = client

                result = await search_procedures(keywords="Cannabis")
                data = json.loads(result)

                assert "count" in data
                assert "procedures" in data


class TestGetCurrentWeek:
    """Tests for get_current_week tool."""

    @pytest.mark.asyncio
    async def test_current_week_structure(self):
        """Test current week returns proper structure."""
        with patch("bundestag_mcp.tools.calendar.get_cache") as cache_mock:
            cache = AsyncMock()
            cache.get.return_value = None
            cache.set.return_value = None
            cache_mock.return_value = cache

            with patch("bundestag_mcp.tools.calendar.get_dip_client") as client_mock:
                client = MagicMock()
                client.search_documents.return_value = []
                client.search_procedures.return_value = []
                client.search_plenary_protocols.return_value = []
                client_mock.return_value = client

                result = await get_current_week()
                data = json.loads(result)

                assert "week" in data
                assert "start" in data["week"]
                assert "end" in data["week"]
                assert "summary" in data
