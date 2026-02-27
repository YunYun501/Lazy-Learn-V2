"""Router for the Material Organizer — auto-categorize course files into folders."""
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.core.config import settings
from app.services.deepseek_provider import DeepSeekProvider
from app.services.document_parser import DocumentParser
from app.services.material_organizer import MaterialOrganizer

router = APIRouter(prefix="/api/organize", tags=["organize"])

# In-memory job state (keyed by job_id)
_job_status: dict = {}


# ------------------------------------------------------------------
# Dependency factories
# ------------------------------------------------------------------


def get_organizer() -> MaterialOrganizer:
    """Create a MaterialOrganizer with real DeepSeek and DocumentParser instances."""
    provider = DeepSeekProvider(api_key=settings.DEEPSEEK_API_KEY)
    parser = DocumentParser()
    return MaterialOrganizer(ai_provider=provider, document_parser=parser)


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------


class OrganizeRequest(BaseModel):
    source_dir: str
    dest_dir: str


class OrganizeResponse(BaseModel):
    job_id: str
    message: str


class OrganizeStatusResponse(BaseModel):
    job_id: str
    status: str
    total_found: int = 0
    total_organized: int = 0
    total_skipped: int = 0
    categories: dict = {}
    error: Optional[str] = None


# ------------------------------------------------------------------
# Background task
# ------------------------------------------------------------------


async def _run_organize(job_id: str, source_dir: str, dest_dir: str) -> None:
    """Background task: run organize_materials and update job status."""
    _job_status[job_id] = {
        "status": "processing",
        "total_found": 0,
        "total_organized": 0,
        "total_skipped": 0,
        "categories": {},
    }
    try:
        organizer = get_organizer()
        result = await organizer.organize_materials(source_dir, dest_dir)
        _job_status[job_id] = {
            "status": "complete",
            "total_found": result.total_found,
            "total_organized": result.total_organized,
            "total_skipped": result.total_skipped,
            "categories": result.categories,
        }
    except Exception as exc:  # noqa: BLE001
        _job_status[job_id] = {
            "status": "error",
            "error": str(exc),
            "total_found": 0,
            "total_organized": 0,
            "total_skipped": 0,
            "categories": {},
        }


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.post("", response_model=OrganizeResponse)
async def organize_materials(
    request: OrganizeRequest,
    background_tasks: BackgroundTasks,
) -> OrganizeResponse:
    """Kick off background organization of files in source_dir → dest_dir.

    Returns a job_id that can be polled via GET /api/organize/{job_id}/status.
    """
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_organize, job_id, request.source_dir, request.dest_dir)
    return OrganizeResponse(job_id=job_id, message="Organization started")


@router.get("/{job_id}/status", response_model=OrganizeStatusResponse)
async def get_organize_status(job_id: str) -> OrganizeStatusResponse:
    """Poll the status of an organization job."""
    status = _job_status.get(job_id, {"status": "not_found"})
    return OrganizeStatusResponse(
        job_id=job_id,
        status=status.get("status", "not_found"),
        total_found=status.get("total_found", 0),
        total_organized=status.get("total_organized", 0),
        total_skipped=status.get("total_skipped", 0),
        categories=status.get("categories", {}),
        error=status.get("error"),
    )
