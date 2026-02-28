import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.services.filesystem import FilesystemManager
from app.services.pdf_parser import PDFParser
from app.services.storage import MetadataStore
from app.services.textbook_finder import TextbookRecommendation, find_textbooks
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
    warning: Optional[str] = None
    progress: int = 0
    step: Optional[str] = None


async def process_pdf_background(textbook_id: str, filepath: str, title: str):
    def set_progress(pct: int, step: str):
        _job_status[textbook_id]["progress"] = pct
        _job_status[textbook_id]["step"] = step

    _job_status[textbook_id] = {"status": "processing", "chapters_found": 0, "progress": 0, "step": "Starting import..."}
    try:
        set_progress(5, "Initializing storage...")
        storage = get_storage()
        await storage.initialize()
        filesystem = get_filesystem()
        parser = PDFParser(storage=storage, filesystem=filesystem)

        set_progress(10, "Checking PDF structure...")
        # Detect flattened PDF early and warn user
        import fitz as _fitz
        _doc = _fitz.open(filepath)
        if parser.is_flattened(_doc):
            _job_status[textbook_id]["warning"] = (
                "\u26a0 This PDF appears to be scanned/image-only. "
                "Text extraction with MinerU may take a very long time "
                "(potentially hours for large documents). "
                "Consider using a text-based PDF if available."
            )
        _doc.close()

        set_progress(15, "Parsing PDF...")
        result = await parser.parse_pdf(filepath, textbook_id, title, on_progress=set_progress)
        _job_status[textbook_id] = {
            "status": "complete",
            "chapters_found": len(result.chapters),
            "progress": 100,
            "step": "Complete!",
        }
    except Exception as e:
        _job_status[textbook_id] = {"status": "error", "error": str(e), "progress": 0, "step": "Failed"}


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
        textbook_id=textbook_id,
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
        warning=status.get("warning"),
        progress=status.get("progress", 0),
        step=status.get("step"),
    )


@router.get("/", response_model=list)
async def list_textbooks(course: Optional[str] = None):
    storage = get_storage()
    await storage.initialize()
    return await storage.list_textbooks(course=course)


@router.delete("/{textbook_id}")
async def delete_textbook(textbook_id: str):
    """Delete a textbook, its chapters, extracted files, and descriptions."""
    storage = get_storage()
    await storage.initialize()
    filesystem = get_filesystem()

    book = await storage.get_textbook(textbook_id)
    if not book:
        raise HTTPException(status_code=404, detail="Textbook not found")

    # Remove files from disk
    textbook_dir = filesystem.data_dir / "textbooks" / textbook_id
    if textbook_dir.exists():
        shutil.rmtree(textbook_dir)

    descriptions_dir = filesystem.data_dir / "descriptions" / textbook_id
    if descriptions_dir.exists():
        shutil.rmtree(descriptions_dir)

    # Remove from database
    await storage.delete_textbook(textbook_id)

    return {"detail": "Textbook deleted", "textbook_id": textbook_id}

@router.get("/{textbook_id}/chapters/{chapter_num}/content")
async def get_chapter_content(textbook_id: str, chapter_num: str):
    """Return the extracted text and image URLs for a specific chapter."""
    storage = get_storage()
    await storage.initialize()
    filesystem = get_filesystem()

    # Read chapter text
    chapter_path = filesystem.data_dir / "textbooks" / textbook_id / "chapters" / f"{chapter_num}.txt"
    if not chapter_path.exists():
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_num} not found")

    text = chapter_path.read_text(encoding="utf-8")

    # Collect image URLs for this chapter (images named page{N}_img{M}.png)
    images_dir = filesystem.data_dir / "textbooks" / textbook_id / "images"
    image_urls = []
    if images_dir.exists():
        for img in sorted(images_dir.glob("*.png")):
            image_urls.append(f"http://127.0.0.1:8000/api/textbooks/{textbook_id}/images/{img.name}")

    # Get chapter metadata from DB
    chapters = await storage.list_chapters(textbook_id)
    chapter_meta = next((c for c in chapters if c["chapter_number"] == chapter_num), None)

    return {
        "textbook_id": textbook_id,
        "chapter_num": chapter_num,
        "title": chapter_meta["title"] if chapter_meta else f"Chapter {chapter_num}",
        "text": text,
        "image_urls": image_urls,
        "page_start": chapter_meta["page_start"] if chapter_meta else 0,
        "page_end": chapter_meta["page_end"] if chapter_meta else 0,
    }


@router.get("/{textbook_id}/images/{filename}")
async def serve_image(textbook_id: str, filename: str):
    """Serve an extracted image file."""
    from fastapi.responses import FileResponse
    filesystem = get_filesystem()
    image_path = filesystem.data_dir / "textbooks" / textbook_id / "images" / filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(image_path))


# ---------------------------------------------------------------------------
# Textbook Finder — AI recommendation endpoint
# ---------------------------------------------------------------------------


class RecommendRequest(BaseModel):
    descriptions: list[str]


@router.post("/recommend", response_model=list[TextbookRecommendation])
async def recommend_textbooks(body: RecommendRequest):
    """Recommend relevant textbooks based on course material descriptions."""
    if not body.descriptions:
        raise HTTPException(status_code=400, detail="At least one description is required")
    from app.services.deepseek_provider import DeepSeekProvider
    provider = DeepSeekProvider(api_key=settings.DEEPSEEK_API_KEY)
    recommendations = await find_textbooks(
        course_descriptions=body.descriptions,
        provider=provider,
    )
    return recommendations
