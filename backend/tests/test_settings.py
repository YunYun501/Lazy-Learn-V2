"""Tests for SettingsStore service and settings router."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.settings import SettingsStore, _mask_value


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def store(tmp_path):
    """Create a SettingsStore with a temporary database."""
    db_path = tmp_path / "test_settings.db"
    s = SettingsStore(db_path=db_path)
    await s.initialize()
    return s


# ---------------------------------------------------------------------------
# Unit tests for _mask_value helper
# ---------------------------------------------------------------------------


def test_mask_value_long_key():
    """Full key is masked — only last 4 chars visible."""
    masked = _mask_value("sk-1234567890abcdefd4c7")
    assert masked.endswith("d4c7")
    assert "1234567890" not in masked
    assert masked.startswith("****...")


def test_mask_value_short_key():
    """Short values (≤4 chars) are not modified."""
    assert _mask_value("abcd") == "abcd"
    assert _mask_value("xy") == "xy"


# ---------------------------------------------------------------------------
# SettingsStore CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_settings_roundtrip(store):
    """Settings save and load correctly."""
    await store.set_setting("download_folder", "/home/user/downloads")
    value = await store.get_setting("download_folder")
    assert value == "/home/user/downloads"


@pytest.mark.asyncio
async def test_settings_update_overwrites(store):
    """Updating a setting overwrites the previous value."""
    await store.set_setting("theme", "dark")
    await store.set_setting("theme", "light")
    value = await store.get_setting("theme")
    assert value == "light"


@pytest.mark.asyncio
async def test_get_setting_returns_none_for_missing(store):
    """get_setting returns None for keys that don't exist."""
    value = await store.get_setting("nonexistent_key")
    assert value is None


# ---------------------------------------------------------------------------
# API key masking tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_key_masked_in_get_all(store):
    """API keys are masked in get_all_settings — only last 4 chars visible."""
    full_key = "sk-1234567890abcdefd4c7"
    await store.set_setting("deepseek_api_key", full_key)
    all_settings = await store.get_all_settings()
    masked = all_settings["deepseek_api_key"]
    assert masked.endswith("d4c7")
    assert masked != full_key
    assert "1234567890" not in masked


@pytest.mark.asyncio
async def test_openai_key_masked_in_get_all(store):
    """OpenAI API keys are also masked in get_all_settings."""
    full_key = "sk-openai-abc1234567890wxyz"
    await store.set_setting("openai_api_key", full_key)
    all_settings = await store.get_all_settings()
    masked = all_settings["openai_api_key"]
    assert masked.endswith("wxyz")
    assert "abc1234567890" not in masked


@pytest.mark.asyncio
async def test_non_api_key_not_masked(store):
    """Non-API key settings are returned unmasked."""
    await store.set_setting("download_folder", "/some/long/path/with/data")
    all_settings = await store.get_all_settings()
    assert all_settings["download_folder"] == "/some/long/path/with/data"


# ---------------------------------------------------------------------------
# Connection test tests (with mocked HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connection_test_success(store):
    """Connection test returns True when API responds with 200."""
    await store.set_setting("deepseek_api_key", "sk-valid-test-key-abcd")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("app.services.settings.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await store.test_connection("deepseek")

    assert result is True


@pytest.mark.asyncio
async def test_connection_test_failure_bad_key(store):
    """Connection test returns False when API responds with 401."""
    await store.set_setting("deepseek_api_key", "sk-invalid-key-xxxx")

    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("app.services.settings.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await store.test_connection("deepseek")

    assert result is False


@pytest.mark.asyncio
async def test_connection_test_no_key_returns_false(store):
    """Connection test returns False immediately if no key is configured."""
    result = await store.test_connection("deepseek")
    assert result is False


@pytest.mark.asyncio
async def test_connection_test_unknown_provider(store):
    """Connection test returns False for unknown provider."""
    result = await store.test_connection("unknown_provider")
    assert result is False


@pytest.mark.asyncio
async def test_connection_test_network_error(store):
    """Connection test returns False when network error occurs."""
    await store.set_setting("deepseek_api_key", "sk-any-key-1234")

    with patch("app.services.settings.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await store.test_connection("deepseek")

    assert result is False
