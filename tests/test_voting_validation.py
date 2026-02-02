"""
Validation tests using real Bundestag voting data.

These tests document expected alignment calculations based on actual
roll-call votes from the Bundestag. They serve as:
1. Proof that our calculation is correct
2. Documentation of the methodology
3. Regression tests if the algorithm changes

Reference Vote: Poll 6391 (2026-01-29)
"Streichung des Straftatbestandes der Politikerbeleidigung"
(Removal of criminal offense for insulting politicians)

Real voting data from AbgeordnetenWatch:
- SPD:       NO  (yes=0,  no=113)
- CDU/CSU:   NO  (yes=0,  no=195)
- AfD:       YES (yes=133, no=0)
- Die Linke: NO  (yes=0,  no=58)
- Grüne:     NO  (yes=0,  no=73)

For this single vote:
- CDU/CSU vs SPD:   ALIGNED (both NO)
- CDU/CSU vs AfD:   NOT ALIGNED (NO vs YES)
- SPD vs AfD:       NOT ALIGNED (NO vs YES)
- CDU/CSU vs Grüne: ALIGNED (both NO)
- SPD vs Grüne:     ALIGNED (both NO)
- AfD vs everyone:  NOT ALIGNED
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from bundestag_mcp.tools.voting import get_party_alignment_score


# Real vote data from Poll 6391 (verified 2026-01-29)
POLL_6391_DATA = {
    "SPD": {"yes": 0, "no": 113, "abstain": 0},
    "CDU/CSU": {"yes": 0, "no": 195, "abstain": 0},
    "AfD": {"yes": 133, "no": 0, "abstain": 0},
    "Die Linke": {"yes": 0, "no": 58, "abstain": 0},
    "BÜNDNIS 90/DIE GRÜNEN": {"yes": 0, "no": 73, "abstain": 0},
}


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
def mock_client_with_real_data():
    """Create a mock client returning real Poll 6391 data."""
    with patch("bundestag_mcp.tools.voting.get_abgeordnetenwatch_client") as mock:
        client = MagicMock()
        client.get_polls.return_value = [
            {
                "id": 6391,
                "label": "Streichung des Straftatbestandes der Politikerbeleidigung",
                "field_poll_date": "2026-01-29",
            }
        ]
        client.aggregate_votes_by_fraction.return_value = POLL_6391_DATA
        mock.return_value = client
        yield client


class TestRealDataValidation:
    """Validation tests using actual Bundestag voting data."""

    @pytest.mark.asyncio
    async def test_cdu_spd_alignment_on_poll_6391(self, mock_cache, mock_client_with_real_data):
        """
        CDU/CSU and SPD both voted NO on Poll 6391.
        Expected: 100% alignment for this single vote.
        """
        result = await get_party_alignment_score(party1="CDU/CSU", party2="SPD", limit=1)
        data = json.loads(result)

        assert data["alignment_percentage"] == 100.0
        assert data["same_vote_count"] == 1
        assert data["vote_details"][0]["aligned"] == True
        assert data["vote_details"][0]["poll_id"] == 6391

    @pytest.mark.asyncio
    async def test_cdu_afd_alignment_on_poll_6391(self, mock_cache, mock_client_with_real_data):
        """
        CDU/CSU voted NO, AfD voted YES on Poll 6391.
        Expected: 0% alignment for this single vote.
        """
        result = await get_party_alignment_score(party1="CDU/CSU", party2="AfD", limit=1)
        data = json.loads(result)

        assert data["alignment_percentage"] == 0.0
        assert data["different_vote_count"] == 1
        assert data["vote_details"][0]["aligned"] == False

    @pytest.mark.asyncio
    async def test_spd_afd_alignment_on_poll_6391(self, mock_cache, mock_client_with_real_data):
        """
        SPD voted NO, AfD voted YES on Poll 6391.
        Expected: 0% alignment for this single vote.
        """
        result = await get_party_alignment_score(party1="SPD", party2="AfD", limit=1)
        data = json.loads(result)

        assert data["alignment_percentage"] == 0.0
        assert data["different_vote_count"] == 1

    @pytest.mark.asyncio
    async def test_all_non_afd_parties_aligned_on_poll_6391(self, mock_cache, mock_client_with_real_data):
        """
        All parties except AfD voted NO on Poll 6391.
        Verify SPD-Grüne alignment is 100%.
        """
        result = await get_party_alignment_score(party1="SPD", party2="Grüne", limit=1)
        data = json.loads(result)

        assert data["alignment_percentage"] == 100.0


class TestAlignmentInterpretation:
    """Test that alignment interpretation text is reasonable."""

    @pytest.mark.asyncio
    async def test_high_alignment_interpretation(self, mock_cache, mock_client_with_real_data):
        """High alignment should indicate near-identical voting."""
        result = await get_party_alignment_score(party1="CDU/CSU", party2="SPD", limit=1)
        data = json.loads(result)

        assert "interpretation" in data
        # 100% alignment should indicate identical voting
        assert "identical" in data["interpretation"].lower()

    @pytest.mark.asyncio
    async def test_low_alignment_interpretation(self, mock_cache, mock_client_with_real_data):
        """Low alignment should indicate opposing positions."""
        result = await get_party_alignment_score(party1="CDU/CSU", party2="AfD", limit=1)
        data = json.loads(result)

        assert "interpretation" in data
        # 0% alignment should indicate opposing positions
        assert "opposing" in data["interpretation"].lower()
