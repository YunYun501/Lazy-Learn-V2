from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.lms_downloader import CourseMaterial, DownloadResult, lms_downloader

router = APIRouter(prefix="/api/lms", tags=["lms"])


class StartRequest(BaseModel):
    lms_url: str


class DownloadRequest(BaseModel):
    material_urls: list[str]
    dest_dir: str


@router.post("/start")
async def start_session(body: StartRequest) -> dict:
    return await lms_downloader.start_session(body.lms_url)


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
        return await lms_downloader.download_materials(
            session_id, body.material_urls, body.dest_dir
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{session_id}")
async def close_session(session_id: str) -> dict:
    await lms_downloader.close_session(session_id)
    return {"status": "closed"}