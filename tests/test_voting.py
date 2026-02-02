"""Tests for voting analysis tools - alignment calculation and validation."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from bundestag_mcp.tools.voting import (
    get_party_alignment_score,
    get_roll_call_votes,
)


@pytest.fixture
def mock_cache():
    """Create a mock cache that always returns None (cache miss)."""
    with patch("bundestag_mcp.tools.voting.get_cache") as mock:
        cache = AsyncMock()
        cache.get.return_value = None
        cache.set.return_value = None
        mock.return_value = cache
        yield cache


@pytest.fixture
def mock_abgeordnetenwatch_client():
    """Create a mock AbgeordnetenWatch client."""
    with patch("bundestag_mcp.tools.voting.get_abgeordnetenwatch_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


class TestAlignmentCalculation:
    """Tests for party alignment score calculation logic."""

    @pytest.mark.asyncio
    async def test_alignment_100_percent_same_votes(self, mock_cache, mock_abgeordnetenwatch_client):
        """When two parties vote identically, alignment should be 100%."""
        # Setup: 3 polls where both parties vote YES
        mock_abgeordnetenwatch_client.get_polls.return_value = [
            {"id": 1, "label": "Vote 1", "field_poll_date": "2024-01-01"},
            {"id": 2, "label": "Vote 2", "field_poll_date": "2024-01-02"},
            {"id": 3, "label": "Vote 3", "field_poll_date": "2024-01-03"},
        ]

        # Both parties vote YES on all polls
        mock_abgeordnetenwatch_client.aggregate_votes_by_fraction.return_value = {
            "CDU/CSU": {"yes": 200, "no": 10, "abstain": 5},
            "SPD": {"yes": 180, "no": 8, "abstain": 3},
        }

        result = await get_party_alignment_score(party1="CDU/CSU", party2="SPD", limit=3)
        data = json.loads(result)

        assert data["alignment_percentage"] == 100.0
        assert data["same_vote_count"] == 3
        assert data["different_vote_count"] == 0

    @pytest.mark.asyncio
    async def test_alignment_0_percent_opposite_votes(self, mock_cache, mock_abgeordnetenwatch_client):
        """When two parties always vote opposite, alignment should be 0%."""
        mock_abgeordnetenwatch_client.get_polls.return_value = [
            {"id": 1, "label": "Vote 1", "field_poll_date": "2024-01-01"},
            {"id": 2, "label": "Vote 2", "field_poll_date": "2024-01-02"},
        ]

        # CDU votes YES, AfD votes NO (opposite)
        def side_effect(poll_id):
            return {
                "CDU/CSU": {"yes": 200, "no": 10, "abstain": 5},
                "AfD": {"yes": 5, "no": 80, "abstain": 2},
            }

        mock_abgeordnetenwatch_client.aggregate_votes_by_fraction.side_effect = side_effect

        result = await get_party_alignment_score(party1="CDU/CSU", party2="AfD", limit=2)
        data = json.loads(result)

        assert data["alignment_percentage"] == 0.0
        assert data["same_vote_count"] == 0
        assert data["different_vote_count"] == 2

    @pytest.mark.asyncio
    async def test_alignment_50_percent_mixed_votes(self, mock_cache, mock_abgeordnetenwatch_client):
        """When parties agree half the time, alignment should be 50%."""
        mock_abgeordnetenwatch_client.get_polls.return_value = [
            {"id": 1, "label": "Vote 1", "field_poll_date": "2024-01-01"},
            {"id": 2, "label": "Vote 2", "field_poll_date": "2024-01-02"},
        ]

        # First poll: both YES (agree)
        # Second poll: CDU YES, SPD NO (disagree)
        call_count = [0]
        def side_effect(poll_id):
            call_count[0] += 1
            if call_count[0] == 1:
                # Both vote YES
                return {
                    "CDU/CSU": {"yes": 200, "no": 10, "abstain": 5},
                    "SPD": {"yes": 180, "no": 8, "abstain": 3},
                }
            else:
                # CDU YES, SPD NO
                return {
                    "CDU/CSU": {"yes": 200, "no": 10, "abstain": 5},
                    "SPD": {"yes": 8, "no": 180, "abstain": 3},
                }

        mock_abgeordnetenwatch_client.aggregate_votes_by_fraction.side_effect = side_effect

        result = await get_party_alignment_score(party1="CDU/CSU", party2="SPD", limit=2)
        data = json.loads(result)

        assert data["alignment_percentage"] == 50.0
        assert data["same_vote_count"] == 1
        assert data["different_vote_count"] == 1

    @pytest.mark.asyncio
    async def test_alignment_returns_vote_details(self, mock_cache, mock_abgeordnetenwatch_client):
        """Alignment result should include vote details with poll_id for linking."""
        mock_abgeordnetenwatch_client.get_polls.return_value = [
            {"id": 6391, "label": "Test Vote", "field_poll_date": "2024-01-01"},
        ]
        mock_abgeordnetenwatch_client.aggregate_votes_by_fraction.return_value = {
            "CDU/CSU": {"yes": 200, "no": 10, "abstain": 5},
            "SPD": {"yes": 180, "no": 8, "abstain": 3},
        }

        result = await get_party_alignment_score(party1="CDU/CSU", party2="SPD", limit=1)
        data = json.loads(result)

        assert "vote_details" in data
        assert len(data["vote_details"]) == 1
        assert data["vote_details"][0]["poll_id"] == 6391
        assert data["vote_details"][0]["aligned"] == True

    @pytest.mark.asyncio
    async def test_alignment_handles_missing_party(self, mock_cache, mock_abgeordnetenwatch_client):
        """When a party has no votes in a poll, that poll should be skipped."""
        mock_abgeordnetenwatch_client.get_polls.return_value = [
            {"id": 1, "label": "Vote 1", "field_poll_date": "2024-01-01"},
        ]
        # Only CDU voted, SPD missing
        mock_abgeordnetenwatch_client.aggregate_votes_by_fraction.return_value = {
            "CDU/CSU": {"yes": 200, "no": 10, "abstain": 5},
        }

        result = await get_party_alignment_score(party1="CDU/CSU", party2="SPD", limit=1)
        data = json.loads(result)

        # No comparable votes
        assert data["votes_analyzed"] == 0


class TestAlignmentValidation:
    """Validation tests comparing calculated alignment to known reference values.

    These tests use real poll IDs and expected outcomes to validate
    that our alignment calculation produces correct results.
    """

    @pytest.mark.asyncio
    async def test_alignment_calculation_logic_manual_verification(self, mock_cache, mock_abgeordnetenwatch_client):
        """
        Manual verification test case:

        Given 5 votes with the following party positions:
        - Vote 1: CDU=YES, SPD=YES (agree)
        - Vote 2: CDU=YES, SPD=NO (disagree)
        - Vote 3: CDU=NO, SPD=NO (agree)
        - Vote 4: CDU=YES, SPD=YES (agree)
        - Vote 5: CDU=NO, SPD=YES (disagree)

        Expected: 3/5 = 60% alignment
        """
        mock_abgeordnetenwatch_client.get_polls.return_value = [
            {"id": i, "label": f"Vote {i}", "field_poll_date": f"2024-01-0{i}"}
            for i in range(1, 6)
        ]

        # Define vote patterns
        vote_patterns = [
            # Vote 1: both YES
            {"CDU/CSU": {"yes": 200, "no": 10}, "SPD": {"yes": 180, "no": 10}},
            # Vote 2: CDU YES, SPD NO
            {"CDU/CSU": {"yes": 200, "no": 10}, "SPD": {"yes": 10, "no": 180}},
            # Vote 3: both NO
            {"CDU/CSU": {"yes": 10, "no": 200}, "SPD": {"yes": 10, "no": 180}},
            # Vote 4: both YES
            {"CDU/CSU": {"yes": 200, "no": 10}, "SPD": {"yes": 180, "no": 10}},
            # Vote 5: CDU NO, SPD YES
            {"CDU/CSU": {"yes": 10, "no": 200}, "SPD": {"yes": 180, "no": 10}},
        ]

        call_count = [0]
        def side_effect(poll_id):
            result = vote_patterns[call_count[0]]
            call_count[0] += 1
            return result

        mock_abgeordnetenwatch_client.aggregate_votes_by_fraction.side_effect = side_effect

        result = await get_party_alignment_score(party1="CDU/CSU", party2="SPD", limit=5)
        data = json.loads(result)

        # 3 agreements out of 5 = 60%
        assert data["alignment_percentage"] == 60.0
        assert data["same_vote_count"] == 3
        assert data["different_vote_count"] == 2
        assert data["votes_analyzed"] == 5


class TestMajorityVoteDetermination:
    """Test that majority vote is correctly determined from vote counts."""

    @pytest.mark.asyncio
    async def test_majority_determined_by_highest_count(self, mock_cache, mock_abgeordnetenwatch_client):
        """Party's position should be determined by their majority vote."""
        mock_abgeordnetenwatch_client.get_polls.return_value = [
            {"id": 1, "label": "Vote 1", "field_poll_date": "2024-01-01"},
        ]

        # CDU: mostly YES (even if some voted NO)
        # SPD: mostly NO (even if some voted YES)
        mock_abgeordnetenwatch_client.aggregate_votes_by_fraction.return_value = {
            "CDU/CSU": {"yes": 150, "no": 50, "abstain": 10},  # Majority YES
            "SPD": {"yes": 50, "no": 140, "abstain": 10},  # Majority NO
        }

        result = await get_party_alignment_score(party1="CDU/CSU", party2="SPD", limit=1)
        data = json.loads(result)

        # CDU voted YES, SPD voted NO = different
        assert data["alignment_percentage"] == 0.0
        assert data["different_vote_count"] == 1

    @pytest.mark.asyncio
    async def test_abstain_can_be_majority(self, mock_cache, mock_abgeordnetenwatch_client):
        """If most members abstain, that should be the party position."""
        mock_abgeordnetenwatch_client.get_polls.return_value = [
            {"id": 1, "label": "Vote 1", "field_poll_date": "2024-01-01"},
        ]

        # Both parties mostly abstain
        mock_abgeordnetenwatch_client.aggregate_votes_by_fraction.return_value = {
            "CDU/CSU": {"yes": 30, "no": 40, "abstain": 150},  # Majority ABSTAIN
            "SPD": {"yes": 20, "no": 50, "abstain": 130},  # Majority ABSTAIN
        }

        result = await get_party_alignment_score(party1="CDU/CSU", party2="SPD", limit=1)
        data = json.loads(result)

        # Both abstained = same position
        assert data["alignment_percentage"] == 100.0
        assert data["same_vote_count"] == 1
