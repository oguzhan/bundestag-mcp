"""DIP API client wrapper using bundestag-api package."""

import os
from functools import lru_cache
from typing import Any

import bundestag_api


class DIPClient:
    """Client for the Bundestag DIP API."""

    def __init__(self, api_key: str | None = None):
        """Initialize the DIP client.

        Args:
            api_key: Optional API key. If not provided, uses BUNDESTAG_API_KEY
                    environment variable or falls back to bundestag-api default.
        """
        self.api_key = api_key or os.getenv("BUNDESTAG_API_KEY")
        self._connection: bundestag_api.btaConnection | None = None

    @property
    def connection(self) -> bundestag_api.btaConnection:
        """Get or create the bundestag-api connection."""
        if self._connection is None:
            if self.api_key:
                self._connection = bundestag_api.btaConnection(apikey=self.api_key)
            else:
                self._connection = bundestag_api.btaConnection()
        return self._connection

    def search_documents(
        self,
        keywords: str | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
        document_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for parliamentary documents (Drucksachen).

        Args:
            keywords: Search terms
            date_start: Start date (YYYY-MM-DD)
            date_end: End date (YYYY-MM-DD)
            document_type: Type of document (e.g., 'Gesetzentwurf')
            limit: Maximum results

        Returns:
            List of document dictionaries
        """
        params = {"limit": min(limit, 50)}

        if keywords:
            params["title"] = [keywords]
        if date_start:
            params["date_start"] = date_start
        if date_end:
            params["date_end"] = date_end
        if document_type:
            params["drucksachetyp"] = [document_type]

        try:
            result = self.connection.search_document(**params)
            return self._normalize_results(result)
        except Exception as e:
            raise RuntimeError(f"Failed to search documents: {e}") from e

    def search_procedures(
        self,
        keywords: str | None = None,
        status: str | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for legislative procedures (Vorgänge).

        Args:
            keywords: Search terms
            status: Filter by status
            date_start: Start date
            date_end: End date
            limit: Maximum results

        Returns:
            List of procedure dictionaries
        """
        params = {"limit": min(limit, 50)}

        if keywords:
            params["title"] = [keywords]
        if date_start:
            params["date_start"] = date_start
        if date_end:
            params["date_end"] = date_end

        try:
            result = self.connection.search_procedure(**params)
            procedures = self._normalize_results(result)

            # Filter by status if provided
            if status:
                procedures = [
                    p for p in procedures
                    if status.lower() in str(p.get("beratungsstand", "")).lower()
                ]

            return procedures
        except Exception as e:
            raise RuntimeError(f"Failed to search procedures: {e}") from e

    def search_plenary_protocols(
        self,
        keywords: str | None = None,
        speaker: str | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search plenary protocols.

        Args:
            keywords: Search in protocol content (uses descriptor/topic search)
            speaker: Filter by speaker name
            date_start: Start date
            date_end: End date
            limit: Maximum results

        Returns:
            List of protocol dictionaries
        """
        try:
            # Use query method directly - title filter requires document/process
            # So we use descriptor for topic-based search or just date filtering
            params: dict[str, Any] = {
                "resource": "plenarprotokoll",
                "limit": min(limit, 50),
            }

            if date_start:
                params["date_start"] = date_start
            if date_end:
                params["date_end"] = date_end

            # Use descriptor for keyword-based topic filtering
            if keywords:
                params["descriptor"] = [keywords]

            result = self.connection.query(**params)

            # Post-filter by speaker name if provided
            if speaker and result:
                # Speaker info may be in the vorgangsbezug or fundstelle
                filtered = []
                for protocol in result:
                    protocol_str = str(protocol).lower()
                    if speaker.lower() in protocol_str:
                        filtered.append(protocol)
                result = filtered if filtered else result[:limit]

            return self._normalize_results(result)
        except Exception as e:
            raise RuntimeError(f"Failed to search plenary protocols: {e}") from e

    def search_persons(
        self,
        name: str | None = None,
        person_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for members of parliament.

        Args:
            name: Name to search for
            person_id: Specific person ID
            limit: Maximum results

        Returns:
            List of person dictionaries
        """
        try:
            if person_id:
                # Use direct query with personID
                result = self.connection.query(
                    resource="person",
                    personID=int(person_id),
                    limit=min(limit, 50),
                )
            elif name:
                # Use person_name filter for name search
                result = self.connection.query(
                    resource="person",
                    person_name=[name],
                    limit=min(limit, 50),
                )
            else:
                # Get recent persons
                result = self.connection.query(
                    resource="person",
                    limit=min(limit, 50),
                )
            return self._normalize_results(result)
        except Exception as e:
            raise RuntimeError(f"Failed to search persons: {e}") from e

    def get_person_by_id(self, person_id: str) -> dict[str, Any] | None:
        """Get a specific person by ID.

        Args:
            person_id: The person's DIP ID

        Returns:
            Person dictionary or None if not found
        """
        try:
            result = self.connection.query(
                resource="person",
                personID=int(person_id),
                limit=1,
            )
            if result and len(result) > 0:
                return self._to_dict(result[0])
            return None
        except Exception:
            return None

    def get_activities(
        self,
        person_id: str | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get activities (Aktivitäten) - includes votes, speeches, etc.

        Args:
            person_id: Filter by person
            date_start: Start date
            date_end: End date
            limit: Maximum results

        Returns:
            List of activity dictionaries
        """
        params = {"limit": min(limit, 50)}

        if date_start:
            params["date_start"] = date_start
        if date_end:
            params["date_end"] = date_end

        try:
            result = self.connection.search_activity(**params)
            activities = self._normalize_results(result)

            # Filter by person if provided
            if person_id:
                activities = [
                    a for a in activities
                    if str(a.get("person_id")) == str(person_id)
                    or any(
                        str(p.get("id")) == str(person_id)
                        for p in a.get("personen", [])
                    )
                ]

            return activities
        except Exception as e:
            raise RuntimeError(f"Failed to get activities: {e}") from e

    def get_current_activities(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent/current activities.

        Returns:
            List of recent activities
        """
        from datetime import datetime, timedelta

        today = datetime.now()
        week_ago = today - timedelta(days=7)

        return self.get_activities(
            date_start=week_ago.strftime("%Y-%m-%d"),
            date_end=today.strftime("%Y-%m-%d"),
            limit=limit,
        )

    def _normalize_results(self, result: Any) -> list[dict[str, Any]]:
        """Normalize API results to a list of dictionaries.

        The bundestag-api returns different types depending on the query.
        This normalizes them to a consistent list of dicts.
        """
        if result is None:
            return []

        if isinstance(result, list):
            return [self._to_dict(item) for item in result]

        if hasattr(result, "__iter__") and not isinstance(result, (str, dict)):
            return [self._to_dict(item) for item in result]

        return [self._to_dict(result)]

    def _to_dict(self, item: Any) -> dict[str, Any]:
        """Convert an item to a dictionary."""
        if isinstance(item, dict):
            return item
        if hasattr(item, "__dict__"):
            return {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
        if hasattr(item, "to_dict"):
            return item.to_dict()
        return {"value": str(item)}


@lru_cache(maxsize=1)
def get_dip_client() -> DIPClient:
    """Get a singleton DIP client instance."""
    return DIPClient()
