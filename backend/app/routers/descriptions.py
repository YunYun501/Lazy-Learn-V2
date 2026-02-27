from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.config import settings
from app.services.deepseek_provider import DeepSeekProvider
from app.services.description_generator import DescriptionGenerator
from app.services.filesystem import FilesystemManager

router = APIRouter(prefix="/api/textbooks", tags=["descriptions"])

_generation_status: dict = {}


def get_filesystem() -> FilesystemManager:
    fs = FilesystemManager(data_dir=settings.DATA_DIR)
    fs.initialize()
    return fs


def get_generator() -> DescriptionGenerator:
    provider = DeepSeekProvider(api_key=settings.DEEPSEEK_API_KEY)
    fs = get_filesystem()
    return DescriptionGenerator(deepseek_provider=provider, filesystem_manager=fs)


async def _run_generation(textbook_id: str):
    _generation_status[textbook_id] = {"status": "processing"}
    try:
        generator = get_generator()
        descriptions = await generator.generate_all_descriptions(textbook_id)
        _generation_status[textbook_id] = {
            "status": "complete",
            "count": len(descriptions),
        }
    except Exception as e:
        _generation_status[textbook_id] = {"status": "error", "error": str(e)}


@router.post("/{textbook_id}/generate-descriptions")
async def generate_descriptions(textbook_id: str, background_tasks: BackgroundTasks):
    """Trigger background AI description generation for all chapters of a textbook."""
    background_tasks.add_task(_run_generation, textbook_id)
    return {"status": "started", "textbook_id": textbook_id}


@router.get("/{textbook_id}/descriptions")
async def list_descriptions(textbook_id: str):
    """List all generated .md description files for a textbook."""
    fs = get_filesystem()
    descriptions_dir = fs.descriptions_dir / textbook_id
    if not descriptions_dir.exists():
        return {"textbook_id": textbook_id, "descriptions": []}

    files = sorted(descriptions_dir.glob("*.md"))
    return {
        "textbook_id": textbook_id,
        "descriptions": [
            {"chapter": f.stem, "path": str(f)}
            for f in files
        ],
    }
