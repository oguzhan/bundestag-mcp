"""AbgeordnetenWatch API client for voting records and MP data."""

import httpx
from typing import Any
from functools import lru_cache


class AbgeordnetenwatchClient:
    """Client for the AbgeordnetenWatch API v2."""

    BASE_URL = "https://www.abgeordnetenwatch.de/api/v2"

    # Bundestag parliament periods
    BUNDESTAG_PERIODS = {
        21: 161,  # Bundestag 2025-2029
        20: 132,  # Bundestag 2021-2025
        19: 128,  # Bundestag 2017-2021
        18: 111,  # Bundestag 2013-2017
    }

    # Party/Fraction IDs for current Bundestag
    FRACTIONS_BT21 = {
        "CDU/CSU": 421,
        "SPD": 425,
        "Grüne": 423,
        "AfD": 420,
        "Die Linke": 422,
        "FDP": 424,  # if applicable
        "BSW": 426,  # Bündnis Sahra Wagenknecht
    }

    def __init__(self, timeout: float = 30.0):
        """Initialize the client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request to the API.

        Args:
            endpoint: API endpoint (e.g., 'polls', 'votes')
            params: Query parameters

        Returns:
            API response data
        """
        url = f"{self.BASE_URL}/{endpoint}"
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_polls(
        self,
        legislature_period: int = 161,  # Current Bundestag
        topic: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get roll-call votes (Abstimmungen).

        Args:
            legislature_period: Parliament period ID (161 = Bundestag 21)
            topic: Filter by topic keyword
            limit: Maximum results

        Returns:
            List of poll dictionaries
        """
        params = {
            "field_legislature": legislature_period,
            "range_end": limit,
        }

        result = self._get("polls", params)
        polls = result.get("data", [])

        # Filter by topic if provided
        if topic and polls:
            topic_lower = topic.lower()
            polls = [
                p for p in polls
                if topic_lower in p.get("label", "").lower()
                or topic_lower in str(p.get("field_intro", "")).lower()
                or any(topic_lower in t.get("label", "").lower() for t in p.get("field_topics", []))
            ]

        return polls

    def get_poll_details(self, poll_id: int) -> dict[str, Any] | None:
        """Get detailed information about a specific poll.

        Args:
            poll_id: The poll ID

        Returns:
            Poll details or None
        """
        try:
            result = self._get(f"polls/{poll_id}")
            return result.get("data")
        except Exception:
            return None

    def get_votes_for_poll(
        self,
        poll_id: int,
        fraction_id: int | None = None,
        limit: int = 700,  # Most Bundestag votes have ~600 MPs
    ) -> list[dict[str, Any]]:
        """Get individual votes for a specific poll.

        Args:
            poll_id: The poll ID
            fraction_id: Optional filter by party/fraction
            limit: Maximum results

        Returns:
            List of vote records
        """
        params = {
            "poll": poll_id,
            "range_end": limit,
        }

        if fraction_id:
            params["fraction"] = fraction_id

        result = self._get("votes", params)
        return result.get("data", [])

    def get_politician(self, politician_id: int) -> dict[str, Any] | None:
        """Get politician details.

        Args:
            politician_id: The politician ID

        Returns:
            Politician data or None
        """
        try:
            result = self._get(f"politicians/{politician_id}")
            return result.get("data")
        except Exception:
            return None

    def search_politicians(
        self,
        name: str | None = None,
        party_id: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for politicians.

        Args:
            name: Name to search for
            party_id: Filter by party
            limit: Maximum results

        Returns:
            List of politician records
        """
        params: dict[str, Any] = {"range_end": limit}

        if party_id:
            params["party"] = party_id

        # Use label[cn] filter for name search (contains)
        if name:
            params["label[cn]"] = name

        result = self._get("politicians", params)
        return result.get("data", [])

    def get_politician_votes(
        self,
        mandate_id: int,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get voting history for a politician's mandate.

        Args:
            mandate_id: The candidacy/mandate ID
            limit: Maximum results

        Returns:
            List of votes
        """
        params = {
            "mandate": mandate_id,
            "range_end": limit,
        }

        result = self._get("votes", params)
        return result.get("data", [])

    def get_mandate_for_politician(
        self,
        politician_id: int,
        legislature_period: int = 161,
    ) -> dict[str, Any] | None:
        """Get the mandate (seat) for a politician in a specific period.

        Args:
            politician_id: The politician ID
            legislature_period: Parliament period ID

        Returns:
            Mandate data or None
        """
        params = {
            "politician": politician_id,
            "parliament_period": legislature_period,
            "range_end": 1,
        }

        try:
            result = self._get("candidacies-mandates", params)
            data = result.get("data", [])
            return data[0] if data else None
        except Exception:
            return None

    def get_fractions(self, legislature_period: int = 161) -> list[dict[str, Any]]:
        """Get all fractions (party groups) for a legislature period.

        Args:
            legislature_period: Parliament period ID

        Returns:
            List of fractions
        """
        params = {
            "legislature": legislature_period,
            "range_end": 20,
        }

        result = self._get("fractions", params)
        return result.get("data", [])

    def aggregate_votes_by_fraction(
        self,
        poll_id: int,
    ) -> dict[str, dict[str, int]]:
        """Aggregate votes by party/fraction for a poll.

        Args:
            poll_id: The poll ID

        Returns:
            Dict mapping fraction name to vote counts
            e.g., {"CDU/CSU": {"yes": 150, "no": 5, "abstain": 2, "no_show": 3}}
        """
        votes = self.get_votes_for_poll(poll_id)

        aggregated: dict[str, dict[str, int]] = {}

        for vote in votes:
            fraction = vote.get("fraction", {})
            fraction_name = fraction.get("label", "Unknown")
            # Clean up fraction name (remove period info)
            if " (" in fraction_name:
                fraction_name = fraction_name.split(" (")[0]

            vote_value = vote.get("vote", "no_show")

            if fraction_name not in aggregated:
                aggregated[fraction_name] = {"yes": 0, "no": 0, "abstain": 0, "no_show": 0}

            if vote_value in aggregated[fraction_name]:
                aggregated[fraction_name][vote_value] += 1

        return aggregated

    def get_topics(self) -> list[dict[str, Any]]:
        """Get all available topics/categories.

        Returns:
            List of topics
        """
        result = self._get("topics", {"range_end": 100})
        return result.get("data", [])


@lru_cache(maxsize=1)
def get_abgeordnetenwatch_client() -> AbgeordnetenwatchClient:
    """Get a singleton AbgeordnetenWatch client instance."""
    return AbgeordnetenwatchClient()
