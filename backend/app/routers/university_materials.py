import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.core.config import get_deepseek_api_key, settings
from app.services.ai_router import AIRouter
from app.services.material_summarizer import MaterialSummarizer
from app.services.relevance_matcher import RelevanceMatcher
from app.services.retroactive_matcher import RetroactiveMatcher
from app.services.storage import MetadataStore

router = APIRouter(prefix="/api/university-materials", tags=["university_materials"])

ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".docx", ".txt", ".md", ".xlsx"}


def get_storage() -> MetadataStore:
    return MetadataStore(db_path=settings.DATA_DIR / "lazy_learn.db")


async def _summarize_and_match_bg(material_id: str, filepath: str, course_id: str) -> None:
    """Background task: summarize uploaded material, then run retroactive matching if textbooks exist."""
    store = get_storage()
    await store.initialize()

    api_key = await get_deepseek_api_key()
    ai_router = AIRouter(deepseek_api_key=api_key, openai_api_key=settings.OPENAI_API_KEY)

    summarizer = MaterialSummarizer(store=store, ai_router=ai_router)
    await summarizer.summarize(material_id, filepath, course_id)

    textbooks = await store.get_course_textbooks(course_id)
    if textbooks:
        relevance_matcher = RelevanceMatcher(store=store, ai_router=ai_router)
        retro_matcher = RetroactiveMatcher(store=store, relevance_matcher=relevance_matcher)
        await retro_matcher.on_material_summarized(course_id)


@router.post("/upload")
async def upload_material(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    course_id: str = Form(...),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: .pdf, .pptx, .docx, .txt, .md, .xlsx",
        )

    storage = get_storage()
    await storage.initialize()

    course = await storage.get_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    dest = (
        settings.DATA_DIR
        / "university_materials"
        / course_id
        / f"{uuid.uuid4()}_{file.filename}"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    dest.write_bytes(content)

    material = await storage.create_university_material(
        course_id=course_id,
        title=file.filename,
        file_type=suffix.lstrip("."),
        filepath=str(dest),
    )

    background_tasks.add_task(_summarize_and_match_bg, material["id"], str(dest), course_id)

    return material


@router.get("")
async def list_materials(course_id: str):
    storage = get_storage()
    await storage.initialize()
    return await storage.list_university_materials(course_id)


@router.delete("/{material_id}")
async def delete_material(material_id: str):
    storage = get_storage()
    await storage.initialize()

    material = await storage.get_university_material(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")

    file_path = Path(material["filepath"])
    if file_path.exists():
        file_path.unlink()

    await storage.delete_university_material(material_id)
    return {"message": "Deleted"}
