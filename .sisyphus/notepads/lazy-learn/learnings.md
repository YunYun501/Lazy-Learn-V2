# Lazy Learn — Learnings

## Conventions & Patterns
- DeepSeek API key: `sk-b7d20f3899e34d80bedcd47890ef4ca7`
- DeepSeek base URL: `https://api.deepseek.com`
- deepseek-chat → Steps 0/2 classification (cheap, 8K output)
- deepseek-reasoner → Step 4 explanations (64K output)
- NO embeddings, NO vector DB — AI reads .md descriptions directly
- Keyword search (Step 1) is pure Python text search — NO AI, NO cost
- Practice problems ALWAYS carry warning: "AI-generated solutions may contain errors. Verify independently."
- LaTeX: use KaTeX via react-katex. NEVER MathJax. NEVER pixelate equations.
- Font: "Press Start 2P" for UI chrome ONLY. Readable fonts for content.

## Test Data
- Textbook: `Simulation Material/Textbook/DigitalControlSystems-NeweditionI.D.LandauG.Zito.pdf`
- Lectures: `Simulation Material/University Material/[Lecture N] MECH0089*.pdf`
- Course: MECH0089 Control and Robotics


## [2026-02-27] Task 1 Spike Complete — Key Findings
- TOC extraction: Generic labels only (front-matter, fulltext, etc.) → AI fallback MANDATORY for chapter naming
- Image extraction: Figures are VECTOR GRAPHICS → use page.get_pixmap(matrix=fitz.Matrix(2,2)) NOT get_images()
- Page rendering: fitz.Matrix(2, 2) zoom → 879×1333px PNG at good quality (~92-154KB per page)
- Equations: Greek chars work (ω = \u03c9), some ASCII approximations for complex expressions
- DeepSeek classification: PASS — valid JSON in ~5.14s, EXPLAINS/USES classification works, confidence 0.9
- DeepSeek streaming: PASS — first chunk 1.63s, 94 total chunks, 5.70s total for 3-sentence response
- DeepSeek LaTeX output: Confirmed — naturally outputs \( \) and $$ delimiters, KaTeX must handle both
- Retry logic: MANDATORY — JSON mode can return empty responses
- Cache optimization: Keep system prompts constant across calls for 10x cheaper cache hits ($0.028/M vs $0.28/M)
## [2026-02-27] Task 2: Backend Scaffolding
- Fixed pyproject.toml build-backend: use "setuptools.build_meta" not "setuptools.backends.legacy:build"
- pytest asyncio_mode = "auto" required for async tests (configured in pyproject.toml)
- CORS origins: localhost:5173 (Vite), localhost:1420 (Tauri dev), tauri://localhost (Tauri prod)
- FastAPI TestClient works seamlessly with pytest fixtures
- Health endpoint test passes: 1 passed in 0.06s
- All dependencies installed successfully: fastapi, uvicorn, pydantic-settings, pytest, pytest-asyncio

## [2026-02-27] Task 5: AI Provider Abstraction Layer
- DeepSeekProvider uses httpx.AsyncClient for all API calls (async/await pattern)
- Retry logic: 3 attempts with exponential backoff delays [2, 4, 8] seconds
- Empty response detection: `if not content or content.strip() == ""` triggers retry
- SYSTEM_PROMPT_PREFIX must be constant across all calls for cache hit optimization (10x cheaper)
- asyncio.sleep MUST be mocked in tests to avoid slow test suite (test_retry_on_empty_response)
- Pydantic models: ConceptExtraction, ClassifiedMatch, Problem, PracticeProblems
- AIProvider abstract base class defines 5 core methods: chat, extract_concepts, classify_matches, generate_explanation, generate_practice_problems
- All 4 tests PASS: concept extraction, classification, retry logic, disclaimer validation
- Test evidence saved: .sisyphus/evidence/task-5-concept-extraction.txt and task-5-retry-logic.txt
- Git commit: e6923d3 (test file) + 182ce5c (provider files)

## [2026-02-27] Task 7: SQLite Metadata Store + Filesystem Layout
- MetadataStore uses aiosqlite with raw SQL (no ORM) — async/await pattern throughout
- Database schema: courses, textbooks, chapters, conversations, messages (5 tables with FKs)
- All CRUD operations return dicts via aiosqlite.Row factory for clean dict conversion
- FilesystemManager handles all path construction — centralized layout logic
- Directory structure: textbooks/{id}/{images,chapters}, descriptions/{id or course_name or math_library}
- Tests use tmp_path fixture for isolation — 3 tests PASS (textbook CRUD, chapter CRUD, filesystem layout)
- Test evidence saved: .sisyphus/evidence/task-7-sqlite-crud.txt
- Git commit: 360d05b (storage + filesystem + tests)

## [2026-02-27] Task 3: Frontend Scaffolding
- Node version: v24.11.0
- npm version: 11.6.1
- Vite version: 7.3.1
- react-katex version: 3.1.0
- vitest version: 4.0.18
- vitest configured with jsdom environment + @testing-library/jest-dom
- KaTeX CSS must be imported in App.tsx: `import 'katex/dist/katex.min.css'`
- vitest.config.ts created separately from vite.config.ts for proper test configuration
- All 3 tests passing: App renders "Lazy Learn" title + 2 KaTeX equation rendering tests
- Frontend directory structure: src/components/, src/api/, src/__tests__/ created
- Dev server verified working on port 5173

## [2026-02-27] Task 6: Description Schema Definition
- .md format: `[EXPLAINS] ConceptName (aliases: alias1, alias2)` — grep-able tags for keyword search
- ChapterDescription Pydantic model: 10 fields including key_concepts list with ConceptEntry objects
- ConceptEntry has: name, aliases, classification (EXPLAINS|USES), description
- serialize_to_md() produces structured markdown with sections: Summary, Key Concepts, Prerequisites, Mathematical Content, Figures
- parse_from_md() uses regex to extract [EXPLAINS]/[USES] tags and reconstruct ChapterDescription from markdown
- search_descriptions() does case-insensitive keyword search across all .md files in directory tree
- Roundtrip test PASSES: serialize → parse preserves all fields including aliases and classifications
- All 4 tests PASS: roundtrip, keyword search, cross-file search, aliases in markdown
- Test evidence saved: .sisyphus/evidence/task-6-roundtrip.txt
- Git commit: 1b338d8 (description schema + manager + tests + example)

## [2026-02-27] Task 4: Tauri Shell
- Tauri version: v2 (configured in Cargo.toml)
- Rust version: NOT INSTALLED (cargo not found)
- cargo check: DEFERRED (Rust toolchain not available)
- Backend spawning: best-effort implementation in src/lib.rs, app works without it
- Window config: 1280x800, title "Lazy Learn", resizable
- Frontend integration: devUrl http://localhost:5173 (Vite dev server)
- Backend integration: Python uvicorn spawned on startup, killed on window close
- Project structure: Complete Tauri v2 scaffold created, ready for compilation
- Status: All files created and committed; awaiting Rust installation for cargo check

## [2026-02-27] Task 9: PPTX/DOCX Parser
- PPTXParser: shape.shape_type == 13 for picture shapes (MSO_SHAPE_TYPE.PICTURE)
- PPTXParser: use enumerate(prs.slides, start=1) for 1-based slide numbers
- DOCXParser: style.name.startswith("Heading") for heading detection (not exact match)
- DOCXParser: parse heading level via int(style_name.replace("Heading ", "")) with ValueError fallback
- DOCXParser: images extracted via doc.part.rels.values() checking "image" in rel.reltype
- DocumentParser: unified dispatcher by file extension (.lower()) — routes .pptx/.docx, rejects .pdf with clear message
- ParsedDocument: total_pages = len(chapters) as simple integer count
- Tests: use tempfile.NamedTemporaryFile(suffix=".pptx/.docx", delete=False) for synthetic test files
- python-pptx and python-docx were already installed from pyproject.toml dependencies
- Both parsers expose to_chapters() returning list[dict] compatible with Task 10 description generator

## [2026-02-27] Task 12: OpenAI Vision Provider (Optional)
- OpenAIProvider.available = bool(api_key and api_key.strip()) — graceful degradation without key
- AIRouter is the single entry point for all AI calls in the app
- Vision tasks: OpenAI GPT-4o (optional), falls back to "not available" message if key not configured
- Text tasks: always DeepSeek (cheaper, 128K context, primary provider)
- OpenAI models: gpt-4o for vision, gpt-4o-mini for text (cheaper fallback)
- Image analysis: base64 encode, detect media type from extension, use data: URI in payload
- All 6 tests PASS: availability checks, fallback messages, router delegation, DeepSeek routing
- Test evidence saved: backend/.sisyphus/evidence/task-12-no-openai.txt
- Git commit: abdfbf1 (openai_provider.py + ai_router.py + test_openai_provider.py)

## [2026-02-27] Task 11: Design System
- CSS custom properties in theme.css (--color-*, --font-*, --space-*, --border-*)
- PixelBadge: EXPLAINS=green (#4caf50), USES=blue (#2196f3)
- PixelDialog: ESC key closes via useEffect + document.addEventListener
- image-rendering: pixelated on * selector, override with auto for content images
- Components live in frontend/src/components/pixel/ barrel-exported from index.ts
- Tests import from '@testing-library/jest-dom' directly (no setupFiles needed — each test file imports it)
- vitest.config.ts uses globals:true + environment:'jsdom' — no setupFiles
- Components tested: PixelButton (3), PixelPanel (2), PixelBadge (2), PixelInput (1), PixelDialog (3) = 11 new tests
- All 14 tests pass (3 original + 11 new pixel component tests)
- theme.css imported in App.tsx as first import for global CSS variables

## [2026-02-27] Task 8: PDF Parser Service
- PDFParser uses PyMuPDF for TOC, text extraction, and image capture with vector-graphic fallback via page.get_pixmap(matrix=fitz.Matrix(2, 2))
- TOC fallback returns a single Full Document chapter when no AI provider is supplied
- Textbooks router supports async import/background parse with status polling via /api/textbooks/{id}/status
- Tests depend on repo-root PDF path; build path from Path(__file__).resolve().parents[2]
- Test evidence saved: .sisyphus/evidence/task-8-pdf-import.txt

## [2026-02-27] Task 10: AI Description Generator
- DESCRIPTION_SYSTEM_PROMPT is a module-level constant for DeepSeek cache hit optimization (10x cheaper)
- _split_text() splits at paragraph boundaries (double newline) when possible, MAX_CHARS_PER_CHUNK = 200_000
- _parse_ai_response() strips markdown code fences (```json) before json.loads()
- Merge strategy: deduplicate concepts by name.lower(), combine math_content, combine figure_descriptions
- summary gets '...' appended when multiple chunks are merged
- generate_all_descriptions() processes chapters sequentially (sorted glob of .txt files)
- descriptions router uses FastAPI BackgroundTasks for async generation
- All 32 backend tests pass (28 existing + 4 new description_generator tests)


## [2026-02-27] Wave 4 Complete — Tasks 19-24
- ExplanationGenerator._build_content() truncation: subtract len(marker) from remaining to stay within MAX_CONTENT_CHARS
- SSE streaming endpoint: `StreamingResponse` with `media_type="text/event-stream"`, each chunk as `data: {chunk}\n\n`, end with `data: [DONE]\n\n`
- PracticeGenerator: ALWAYS enforce disclaimer via _enforce_disclaimer() even if AI omits it
- ConversationHandler: loads full history from SQLite, prepends system prompt, saves user+assistant messages after streaming
- MetadataStore: added create_conversation, add_message, get_messages methods
- SearchResults component: PixelButton doesn't spread props, wrap in div for data-testid
- ExplanationView: uses fetch() with ReadableStream reader for SSE, AbortController for cleanup
- TextbookViewer: image navigation with currentImageIdx state, prev/next buttons
- Backend chapter content endpoint: GET /api/textbooks/{id}/chapters/{num}/content returns text + image_urls
- Backend image serving: GET /api/textbooks/{id}/images/{filename} via FileResponse
- Frontend test counts: 45 tests passing (9 test files)
- Backend test counts: 55 tests passing