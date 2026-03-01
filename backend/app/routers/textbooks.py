import shutil
import uuid
from typing import Optional

import fitz

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import get_deepseek_api_key, settings
from app.models.pipeline_models import ChapterVerificationRequest, ChapterWithStatus, ExtractionStatus, PipelineStatus
from app.services.ai_router import AIRouter
from app.services.content_extractor import ContentExtractor
from app.services.filesystem import FilesystemManager
from app.services.pdf_parser import PDFParser
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.relevance_matcher import RelevanceMatcher
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
    status: str
    message: str


class StatusResponse(BaseModel):
    textbook_id: str
    pipeline_status: str
    chapters: list[ChapterWithStatus] = []
    relevance_results: Optional[list[dict]] = None
    status: Optional[str] = None
    chapters_found: int = 0
    error: Optional[str] = None
    warning: Optional[str] = None
    progress: int = 0
    step: Optional[str] = None


def _coerce_int(value: Optional[str], default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _build_subsections(toc_entries: list[dict], section_start: int, section_end: int) -> list[dict]:
    """Build level-3 sub-sections within a level-2 section's page range."""
    subs = [
        entry
        for entry in toc_entries
        if entry.get("level") == 3 and section_start <= entry.get("page", 1) <= section_end
    ]
    subs.sort(key=lambda entry: entry.get("page", 1))
    built: list[dict] = []
    for idx, entry in enumerate(subs):
        sub_start = _coerce_int(entry.get("page", 1), 1)
        next_page = subs[idx + 1].get("page") if idx + 1 < len(subs) else None
        sub_end = _coerce_int(next_page, section_end + 1) - 1 if next_page else section_end
        built.append(
            {
                "section_number": idx + 1,
                "title": entry.get("title", ""),
                "page_start": sub_start,
                "page_end": sub_end,
            }
        )
    return built


def _build_sections(toc_entries: list[dict], page_start: int, page_end: int) -> list[dict]:
    sections = [
        entry
        for entry in toc_entries
        if entry.get("level") == 2 and page_start <= entry.get("page", 1) <= page_end
    ]
    sections.sort(key=lambda entry: entry.get("page", 1))
    built: list[dict] = []
    for idx, entry in enumerate(sections):
        section_start = _coerce_int(entry.get("page", 1), 1)
        next_page = sections[idx + 1].get("page") if idx + 1 < len(sections) else None
        section_end = _coerce_int(next_page, page_end + 1) - 1 if next_page else page_end
        built.append(
            {
                "section_number": idx + 1,
                "title": entry.get("title", ""),
                "page_start": section_start,
                "page_end": section_end,
                "subsections": _build_subsections(toc_entries, section_start, section_end),
            }
        )
    return built


def _build_toc_payload(toc_entries: list[dict], total_pages: int) -> dict:
    top_level = [entry for entry in toc_entries if entry.get("level") == 1]
    if not top_level:
        return {
            "chapters": [
                {
                    "chapter_number": "1",
                    "title": "Full Document",
                    "page_start": 1,
                    "page_end": total_pages,
                    "sections": [],
                }
            ]
        }

    chapters: list[dict] = []
    for idx, entry in enumerate(top_level):
        page_start = _coerce_int(entry.get("page", 1), 1)
        next_page = top_level[idx + 1].get("page") if idx + 1 < len(top_level) else None
        page_end = _coerce_int(next_page, total_pages + 1) - 1 if next_page else total_pages
        chapters.append(
            {
                "chapter_number": str(idx + 1),
                "title": entry.get("title", ""),
                "page_start": page_start,
                "page_end": page_end,
                "sections": _build_sections(toc_entries, page_start, page_end),
            }
        )
    return {"chapters": chapters}


class TocExtractionService:
    def __init__(self, store: MetadataStore, filesystem: FilesystemManager) -> None:
        self.store = store
        self.filesystem = filesystem
        self.parser = PDFParser(storage=store, filesystem=filesystem)

    async def extract_toc(self, textbook_id: str) -> dict:
        textbook = await self.store.get_textbook(textbook_id)
        if not textbook:
            raise ValueError("Textbook not found")
        filepath = textbook.get("filepath")
        doc = fitz.open(filepath)
        try:
            toc_entries = self.parser.extract_toc(doc)
            if not toc_entries:
                toc_entries = await self.parser.ai_toc_fallback(doc)
            return _build_toc_payload(toc_entries, len(doc))
        finally:
            doc.close()


async def process_pdf_background(textbook_id: str):
    _job_status[textbook_id] = {
        "status": "processing",
        "chapters_found": 0,
        "progress": 10,
        "step": "Extracting table of contents...",
    }
    try:
        storage = get_storage()
        await storage.initialize()
        filesystem = get_filesystem()
        toc_service = TocExtractionService(storage, filesystem)
        api_key = await get_deepseek_api_key()
        ai_router = AIRouter(deepseek_api_key=api_key, openai_api_key=settings.OPENAI_API_KEY)
        relevance_service = RelevanceMatcher(store=storage, ai_router=ai_router)
        extraction_service = ContentExtractor(store=storage)
        orchestrator = PipelineOrchestrator(
            store=storage,
            toc_service=toc_service,
            relevance_service=relevance_service,
            extraction_service=extraction_service,
        )
        result = await orchestrator.run_toc_phase(textbook_id)

        chapters = result.get("chapters", [])
        relevance_results = result.get("relevance_results", [])
        if len(chapters) == 1:
            await storage.update_chapter_extraction_status(
                chapters[0]["id"],
                ExtractionStatus.selected.value,
            )

        pipeline_status = result.get("pipeline_status", "toc_extracted")
        _job_status[textbook_id] = {
            "status": pipeline_status,
            "chapters_found": len(chapters),
            "progress": 0 if pipeline_status == PipelineStatus.error.value else 100,
            "step": "Failed" if pipeline_status == PipelineStatus.error.value else "TOC extracted",
            "relevance_results": relevance_results,
            "error": result.get("error"),
        }
    except Exception as exc:
        _job_status[textbook_id] = {
            "status": "error",
            "error": str(exc),
            "progress": 0,
            "step": "Failed",
        }


@router.post("/import", response_model=ImportResponse)
async def import_textbook(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    course: Optional[str] = None,
    course_id: Optional[str] = Form(None),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    textbook_id = str(uuid.uuid4())
    storage = get_storage()
    await storage.initialize()

    # Validate course_id if provided
    if course_id:
        course_record = await storage.get_course(course_id)
        if course_record is None:
            raise HTTPException(status_code=404, detail="Course not found")

    filesystem = get_filesystem()

    dirs = filesystem.setup_textbook_dirs(textbook_id)
    dest_path = dirs["base"] / "original.pdf"
    content = await file.read()
    dest_path.write_bytes(content)

    orchestrator = PipelineOrchestrator(store=storage)
    start_result = await orchestrator.start_import(
        textbook_id=textbook_id,
        course_id=course_id,
        file_path=str(dest_path),
    )

    _job_status[textbook_id] = {
        "status": start_result.get("pipeline_status", "uploaded"),
        "chapters_found": 0,
        "progress": 0,
        "step": "Uploaded",
        "error": start_result.get("error"),
    }

    if start_result.get("pipeline_status") != PipelineStatus.error.value:
        background_tasks.add_task(process_pdf_background, textbook_id)

    return ImportResponse(
        textbook_id=textbook_id,
        job_id=textbook_id,
        status=start_result.get("pipeline_status", "uploaded"),
        message="Processing started",
    )


@router.get("/{textbook_id}/status", response_model=StatusResponse)
async def get_status(textbook_id: str):
    storage = get_storage()
    await storage.initialize()
    textbook = await storage.get_textbook(textbook_id)

    pipeline_status: str = (textbook.get("pipeline_status") if textbook else None) or "not_found"
    chapters = await storage.list_chapters(textbook_id) if textbook else []
    legacy = _job_status.get(textbook_id, {})
    relevance_results = legacy.get("relevance_results")
    relevance_map = {item.get("chapter_id"): item for item in (relevance_results or [])}

    chapter_payload = []
    for chapter in chapters:
        relevance = relevance_map.get(chapter.get("id"), {})
        chapter_payload.append(
            ChapterWithStatus(
                id=chapter.get("id", ""),
                title=chapter.get("title", ""),
                chapter_number=_coerce_int(chapter.get("chapter_number"), 0),
                page_start=_coerce_int(chapter.get("page_start"), 0),
                page_end=_coerce_int(chapter.get("page_end"), 0),
                extraction_status=chapter.get(
                    "extraction_status",
                    ExtractionStatus.pending.value,
                ),
                relevance_score=relevance.get("relevance_score"),
                matched_topics=relevance.get("matched_topics"),
            )
        )

    return StatusResponse(
        textbook_id=textbook_id,
        pipeline_status=pipeline_status,
        chapters=chapter_payload,
        relevance_results=relevance_results,
        status=legacy.get("status", pipeline_status),
        chapters_found=legacy.get("chapters_found", len(chapter_payload)),
        error=legacy.get("error"),
        warning=legacy.get("warning"),
        progress=legacy.get("progress", 0),
        step=legacy.get("step"),
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


@router.get("/{textbook_id}/chapters/{chapter_id}/sections")
async def get_chapter_sections(textbook_id: str, chapter_id: str):
    """Return sections (subchapters) for a given chapter."""
    storage = get_storage()
    await storage.initialize()
    sections = await storage.get_sections_for_chapter(chapter_id)
    return sections


@router.get("/{textbook_id}/sections/{section_id}/subsections")
async def get_section_subsections(textbook_id: str, section_id: str):
    """Return sub-sections (level 3) for a given section."""
    storage = get_storage()
    await storage.initialize()
    subsections = await storage.get_subsections_for_section(section_id)
    return subsections

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


# ---------------------------------------------------------------------------
# Chapter verification and deferred extraction endpoints
# ---------------------------------------------------------------------------


class ExtractDeferredRequest(BaseModel):
    chapter_ids: list[str]


@router.post("/{textbook_id}/verify-chapters")
async def verify_chapters(
    textbook_id: str,
    body: ChapterVerificationRequest,
    background_tasks: BackgroundTasks,
):
    """Select chapters for extraction. Textbook must be in toc_extracted state."""
    storage = get_storage()
    await storage.initialize()

    textbook = await storage.get_textbook(textbook_id)
    if not textbook:
        raise HTTPException(status_code=404, detail="Textbook not found")

    if textbook.get("pipeline_status") != PipelineStatus.toc_extracted.value:
        raise HTTPException(
            status_code=409,
            detail=f"Textbook must be in '{PipelineStatus.toc_extracted.value}' state to verify chapters",
        )

    extraction_service = ContentExtractor(store=storage)
    orchestrator = PipelineOrchestrator(store=storage, extraction_service=extraction_service)
    await orchestrator.submit_verification(textbook_id, body.selected_chapter_ids)
    background_tasks.add_task(
        orchestrator.run_extraction_phase, textbook_id, body.selected_chapter_ids
    )

    return {"status": "extracting", "selected_count": len(body.selected_chapter_ids)}


@router.post("/{textbook_id}/extract-deferred")
async def extract_deferred(
    textbook_id: str,
    body: ExtractDeferredRequest,
    background_tasks: BackgroundTasks,
):
    """Extract previously deferred chapters. Textbook must be partially or fully extracted."""
    storage = get_storage()
    await storage.initialize()

    textbook = await storage.get_textbook(textbook_id)
    if not textbook:
        raise HTTPException(status_code=404, detail="Textbook not found")

    valid_states = {
        PipelineStatus.partially_extracted.value,
        PipelineStatus.fully_extracted.value,
    }
    if textbook.get("pipeline_status") not in valid_states:
        raise HTTPException(
            status_code=409,
            detail="Textbook must be in 'partially_extracted' or 'fully_extracted' state",
        )

    extraction_service = ContentExtractor(store=storage)
    orchestrator = PipelineOrchestrator(store=storage, extraction_service=extraction_service)
    await orchestrator.run_deferred_extraction(textbook_id, body.chapter_ids)
    background_tasks.add_task(
        orchestrator.run_extraction_phase, textbook_id, body.chapter_ids
    )

    return {"status": "extracting"}


@router.get("/{textbook_id}/extraction-progress")
async def extraction_progress(textbook_id: str):
    """Return per-chapter extraction status and overall pipeline status."""
    storage = get_storage()
    await storage.initialize()

    textbook = await storage.get_textbook(textbook_id)
    if not textbook:
        raise HTTPException(status_code=404, detail="Textbook not found")

    chapters = await storage.list_chapters(textbook_id)
    return {
        "pipeline_status": textbook.get("pipeline_status", "unknown"),
        "chapters": [
            {
                "id": ch["id"],
                "title": ch["title"],
                "chapter_number": ch["chapter_number"],
                "page_start": ch["page_start"],
                "page_end": ch["page_end"],
                "extraction_status": ch.get("extraction_status", "pending"),
            }
            for ch in chapters
        ],
    }
