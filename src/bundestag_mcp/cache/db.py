"""SQLite caching layer for Bundestag data."""

import json
import hashlib
import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class Cache:
    """SQLite-based cache for API responses."""

    DEFAULT_TTL_HOURS = 24  # Cache validity in hours

    def __init__(self, db_path: str | Path | None = None):
        """Initialize the cache.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.bundestag_mcp/cache.db
        """
        if db_path is None:
            cache_dir = Path.home() / ".bundestag_mcp"
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = cache_dir / "cache.db"

        self.db_path = Path(db_path)
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure the database tables exist."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    ttl_hours INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_created
                ON cache(created_at)
            """)
            await db.commit()

        self._initialized = True

    def _make_key(self, namespace: str, params: dict[str, Any]) -> str:
        """Create a cache key from namespace and parameters.

        Args:
            namespace: The type of data being cached (e.g., 'documents', 'persons')
            params: The query parameters

        Returns:
            A hash-based cache key
        """
        # Sort params for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        content = f"{namespace}:{sorted_params}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def get(
        self,
        namespace: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]] | None:
        """Get cached data if valid.

        Args:
            namespace: The data namespace
            params: Query parameters used as cache key

        Returns:
            Cached data or None if not found/expired
        """
        await self._ensure_initialized()

        key = self._make_key(namespace, params)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value, created_at, ttl_hours FROM cache WHERE key = ?",
                (key,)
            ) as cursor:
                row = await cursor.fetchone()

        if row is None:
            return None

        value_json, created_at_str, ttl_hours = row
        created_at = datetime.fromisoformat(created_at_str)

        # Check if cache is still valid
        if datetime.now() - created_at > timedelta(hours=ttl_hours):
            # Cache expired, delete it
            await self.delete(namespace, params)
            return None

        try:
            return json.loads(value_json)
        except json.JSONDecodeError:
            return None

    async def set(
        self,
        namespace: str,
        params: dict[str, Any],
        value: list[dict[str, Any]],
        ttl_hours: int | None = None,
    ) -> None:
        """Store data in cache.

        Args:
            namespace: The data namespace
            params: Query parameters used as cache key
            value: The data to cache
            ttl_hours: How long to cache (default: 24 hours)
        """
        await self._ensure_initialized()

        if ttl_hours is None:
            ttl_hours = self.DEFAULT_TTL_HOURS

        key = self._make_key(namespace, params)
        value_json = json.dumps(value, default=str)
        created_at = datetime.now().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO cache (key, value, created_at, ttl_hours)
                VALUES (?, ?, ?, ?)
                """,
                (key, value_json, created_at, ttl_hours)
            )
            await db.commit()

    async def delete(self, namespace: str, params: dict[str, Any]) -> None:
        """Delete a cache entry.

        Args:
            namespace: The data namespace
            params: Query parameters
        """
        await self._ensure_initialized()

        key = self._make_key(namespace, params)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM cache WHERE key = ?", (key,))
            await db.commit()

    async def clear_expired(self) -> int:
        """Remove all expired cache entries.

        Returns:
            Number of entries removed
        """
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            # Get count before deletion
            async with db.execute("SELECT COUNT(*) FROM cache") as cursor:
                before = (await cursor.fetchone())[0]

            # Delete expired entries
            await db.execute("""
                DELETE FROM cache
                WHERE datetime(created_at, '+' || ttl_hours || ' hours') < datetime('now')
            """)
            await db.commit()

            # Get count after deletion
            async with db.execute("SELECT COUNT(*) FROM cache") as cursor:
                after = (await cursor.fetchone())[0]

        return before - after

    async def clear_all(self) -> None:
        """Clear all cached data."""
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM cache")
            await db.commit()

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM cache") as cursor:
                total = (await cursor.fetchone())[0]

            async with db.execute("""
                SELECT COUNT(*) FROM cache
                WHERE datetime(created_at, '+' || ttl_hours || ' hours') < datetime('now')
            """) as cursor:
                expired = (await cursor.fetchone())[0]

        return {
            "total_entries": total,
            "expired_entries": expired,
            "valid_entries": total - expired,
            "db_path": str(self.db_path),
        }


# Global cache instance
_cache: Cache | None = None


def get_cache() -> Cache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
