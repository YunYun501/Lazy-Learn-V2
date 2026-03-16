from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.lms_downloader import CourseMaterial, DownloadResult, lms_downloader

router = APIRouter(prefix="/api/lms", tags=["lms"])


class StartRequest(BaseModel):
    lms_url: str


class DownloadRequest(BaseModel):
    material_urls: list[str]
    dest_dir: str


def _validate_lms_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs are allowed")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid URL")
    blocked = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "169.254.169.254",
        "metadata.google.internal",
    }
    if parsed.hostname.lower() in blocked:
        raise HTTPException(status_code=400, detail="URL targets a restricted address")
    return url


def _validate_dest_dir(dest_dir: str) -> str:
    data_dir = settings.DATA_DIR.resolve()
    resolved = Path(dest_dir).resolve()
    if not str(resolved).startswith(str(data_dir)):
        raise HTTPException(
            status_code=400,
            detail="Destination must be within the application data directory",
        )
    return str(resolved)


@router.post("/start")
async def start_session(body: StartRequest) -> dict:
    validated_url = _validate_lms_url(body.lms_url)
    return await lms_downloader.start_session(validated_url)


@router.get("/{session_id}/status")
async def get_status(session_id: str) -> dict:
    status = await lms_downloader.check_login_status(session_id)
    return {"status": status}


@router.get("/{session_id}/materials", response_model=list[CourseMaterial])
async def list_materials(session_id: str, course_url: str) -> list[CourseMaterial]:
    try:
        return await lms_downloader.list_course_materials(session_id, course_url)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{session_id}/download", response_model=DownloadResult)
async def download_materials(session_id: str, body: DownloadRequest) -> DownloadResult:
    try:
        validated_dest = _validate_dest_dir(body.dest_dir)
        return await lms_downloader.download_materials(
            session_id, body.material_urls, validated_dest
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{session_id}")
async def close_session(session_id: str) -> dict:
    await lms_downloader.close_session(session_id)
    return {"status": "closed"}
