"""Settings persistence service using SQLite (aiosqlite).

Note: API keys are stored in SQLite which is acceptable for a local desktop application.
      Keys are masked in all API responses — only the last 4 characters are shown.
"""
import aiosqlite
import httpx
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path("data/lazy_learn.db")

# Keys that are considered API keys and should be masked in GET responses
_API_KEY_NAMES = {"deepseek_api_key", "openai_api_key"}

CREATE_SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _mask_value(value: str) -> str:
    """Show only the last 4 characters, replacing the rest with asterisks."""
    if len(value) <= 4:
        return value
    return "****..." + value[-4:]


class SettingsStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    async def initialize(self):
        """Create settings table if it doesn't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(CREATE_SETTINGS_TABLE_SQL)
            await db.commit()

    async def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value by key. Returns None if not found."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row["value"] if row else None

    async def set_setting(self, key: str, value: str):
        """Insert or update a setting."""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value,"
                " updated_at = excluded.updated_at",
                (key, value, now),
            )
            await db.commit()

    async def get_all_settings(self) -> dict:
        """Return all settings. API key values are masked (last 4 chars only)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT key, value FROM settings") as cursor:
                rows = await cursor.fetchall()
        result = {}
        for row in rows:
            key = row["key"]
            value = row["value"]
            if key in _API_KEY_NAMES and value:
                result[key] = _mask_value(value)
            else:
                result[key] = value
        return result

    async def test_connection(self, provider: str) -> bool:
        """Make a minimal API call to verify the configured key works.

        Args:
            provider: 'deepseek' or 'openai'

        Returns:
            True if the connection succeeded, False otherwise.
        """
        if provider == "deepseek":
            key = await self.get_setting("deepseek_api_key")
            if not key:
                return False
            url = "https://api.deepseek.com/chat/completions"
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            }
        elif provider == "openai":
            key = await self.get_setting("openai_api_key")
            if not key:
                return False
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            }
        else:
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                return response.status_code == 200
        except Exception:
            return False
