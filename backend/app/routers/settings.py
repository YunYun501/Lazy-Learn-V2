"""Router for settings management — API keys, download folder, course config."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings as app_config
from app.services.settings import SettingsStore

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_settings_store() -> SettingsStore:
    """Create a SettingsStore using the main data directory."""
    db_path = app_config.DATA_DIR / "lazy_learn.db"
    return SettingsStore(db_path=db_path)


class SettingUpdate(BaseModel):
    key: str
    value: str


class ConnectionTestRequest(BaseModel):
    provider: str  # "deepseek" | "openai"


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str


@router.get("")
async def get_settings() -> dict:
    """Return all settings with API keys masked."""
    store = get_settings_store()
    await store.initialize()
    return await store.get_all_settings()


@router.put("")
async def update_setting(body: SettingUpdate) -> dict:
    """Update a single setting by key."""
    store = get_settings_store()
    await store.initialize()
    await store.set_setting(body.key, body.value)
    return {"success": True, "key": body.key}


@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_connection(body: ConnectionTestRequest) -> ConnectionTestResponse:
    """Test an API provider connection by making a minimal API call."""
    store = get_settings_store()
    await store.initialize()

    # Check if key is configured first
    key = await store.get_setting(f"{body.provider}_api_key")
    if not key:
        return ConnectionTestResponse(
            success=False,
            message=f"No {body.provider.capitalize()} API key configured",
        )

    success = await store.test_connection(body.provider)
    if success:
        return ConnectionTestResponse(
            success=True,
            message=f"{body.provider.capitalize()} connection successful",
        )
    return ConnectionTestResponse(
        success=False,
        message=f"{body.provider.capitalize()} connection failed — check your API key",
    )
