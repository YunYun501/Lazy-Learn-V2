import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.services.filesystem import FilesystemManager
from app.services.pdf_parser import PDFParser
from app.services.storage import MetadataStore

router = APIRouter(prefix="/api/textbooks", tags=["textbooks"])

_job_status: dict = {}


def get_storage() -> MetadataStore:
    return MetadataStore(db_path=settings.DATA_DIR / "lazy_learn.db")


def get_filesystem() -> FilesystemManager:
    fs = FilesystemManager(data_dir=settings.DATA_DIR)
    fs.initialize()
    return fs


class ImportResponse(BaseModel):
    textbook_id: str
    job_id: str
    message: str


class StatusResponse(BaseModel):
    textbook_id: str
    status: str
    chapters_found: int = 0
    error: Optional[str] = None


async def process_pdf_background(textbook_id: str, filepath: str, title: str):
    _job_status[textbook_id] = {"status": "processing", "chapters_found": 0}
    try:
        storage = get_storage()
        await storage.initialize()
        filesystem = get_filesystem()
        parser = PDFParser(storage=storage, filesystem=filesystem)
        result = await parser.parse_pdf(filepath, textbook_id, title)
        _job_status[textbook_id] = {
            "status": "complete",
            "chapters_found": len(result.chapters),
        }
    except Exception as e:
        _job_status[textbook_id] = {"status": "error", "error": str(e)}


@router.post("/import", response_model=ImportResponse)
async def import_textbook(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    course: Optional[str] = None,
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    textbook_id = str(uuid.uuid4())
    storage = get_storage()
    await storage.initialize()
    filesystem = get_filesystem()

    dirs = filesystem.setup_textbook_dirs(textbook_id)
    dest_path = dirs["base"] / "original.pdf"
    content = await file.read()
    dest_path.write_bytes(content)

    title = file.filename.replace(".pdf", "").replace("_", " ")
    await storage.create_textbook(
        title=title,
        filepath=str(dest_path),
        course=course,
        library_type="course",
    )

    background_tasks.add_task(process_pdf_background, textbook_id, str(dest_path), title)

    return ImportResponse(
        textbook_id=textbook_id,
        job_id=textbook_id,
        message="Processing started",
    )


@router.get("/{textbook_id}/status", response_model=StatusResponse)
async def get_status(textbook_id: str):
    status = _job_status.get(textbook_id, {"status": "not_found"})
    return StatusResponse(
        textbook_id=textbook_id,
        status=status.get("status", "not_found"),
        chapters_found=status.get("chapters_found", 0),
        error=status.get("error"),
    )


@router.get("/", response_model=list)
async def list_textbooks(course: Optional[str] = None):
    storage = get_storage()
    await storage.initialize()
    return await storage.list_textbooks(course=course)
