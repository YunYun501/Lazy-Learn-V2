from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.models.ai_models import ClassifiedMatch, ConceptExtraction
from app.services.concept_extractor import ConceptExtractor
from app.services.deepseek_provider import DeepSeekProvider
from app.services.filesystem import FilesystemManager
from app.services.keyword_search import SearchHit, search_descriptions
from app.services.match_categorizer import MatchCategorizer

router = APIRouter(prefix="/api/search", tags=["search"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def get_deepseek() -> DeepSeekProvider:
    return DeepSeekProvider(api_key=settings.DEEPSEEK_API_KEY)


def get_filesystem() -> FilesystemManager:
    fs = FilesystemManager(data_dir=settings.DATA_DIR)
    fs.initialize()
    return fs


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ExtractConceptsRequest(BaseModel):
    query: str


class KeywordSearchRequest(BaseModel):
    keywords: list[str]
    library_type: str | None = None  # 'math', 'course', or None for both


class CategorizeRequest(BaseModel):
    matches: list[SearchHit]
    concept: str


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    query: str
    concepts: list[str]
    equations: list[str]
    categorized_matches: list[ClassifiedMatch]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/extract-concepts", response_model=ConceptExtraction)
async def extract_concepts(request: ExtractConceptsRequest) -> ConceptExtraction:
    """Step 0: Extract concepts and equation forms from a student's query."""
    extractor = ConceptExtractor(deepseek_provider=get_deepseek())
    return await extractor.extract(request.query)


@router.post("/keyword", response_model=list[SearchHit])
async def keyword_search(request: KeywordSearchRequest) -> list[SearchHit]:
    """Step 1: Keyword search across all .md description files."""
    fs = get_filesystem()
    return search_descriptions(
        descriptions_dir=fs.descriptions_dir,
        keywords=request.keywords,
        library_type=request.library_type,
    )


@router.post("/categorize", response_model=list[ClassifiedMatch])
async def categorize_matches(request: CategorizeRequest) -> list[ClassifiedMatch]:
    """Step 2: AI categorization of search hits as EXPLAINS or USES."""
    categorizer = MatchCategorizer(deepseek_provider=get_deepseek())
    return await categorizer.categorize(request.matches, request.concept)


@router.post("/query", response_model=QueryResponse)
async def full_search_query(request: QueryRequest) -> QueryResponse:
    """Combined Steps 0+1+2: Extract concepts -> keyword search -> AI categorize.

    This is the main search endpoint used by the frontend.
    """
    provider = get_deepseek()
    fs = get_filesystem()

    # Step 0: Extract concepts
    extractor = ConceptExtractor(deepseek_provider=provider)
    extraction = await extractor.extract(request.query)

    # Step 1: Keyword search using extracted concepts
    all_keywords = extraction.concepts + extraction.equations
    if not all_keywords:
        all_keywords = [request.query]  # Fallback: search raw query

    hits = search_descriptions(
        descriptions_dir=fs.descriptions_dir,
        keywords=all_keywords,
    )

    # Step 2: Categorize hits (if any)
    categorized: list[ClassifiedMatch] = []
    if hits and extraction.concepts:
        categorizer = MatchCategorizer(deepseek_provider=provider)
        concept = extraction.concepts[0]  # Use primary concept for categorization
        categorized = await categorizer.categorize(hits, concept)

    return QueryResponse(
        query=request.query,
        concepts=extraction.concepts,
        equations=extraction.equations,
        categorized_matches=categorized,
    )
