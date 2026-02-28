# Content Pipeline Redesign — Learnings

## [2026-02-28] Session Init — Architecture Research

### Key Files
- `backend/app/services/mineru_parser.py` — MinerU integration. `do_parse()` at lines 46-84. `start_page_id=0, end_page_id=None` params at line 50-51 (NEVER tested with non-default values). Content iteration at line 67 only checks `type == "discarded"` — other types unknown.
- `backend/app/services/storage.py` — MetadataStore. Table creation in `initialize()` at lines 14-72. Migration pattern (try/except ALTER TABLE) at lines 74-79. CRUD methods at 81-160.
- `backend/app/routers/textbooks.py` — Current import pipeline. `process_pdf_background()` at lines 44-79. `_job_status` in-memory dict at line 15.
- `backend/app/services/pdf_parser.py` — TOC extraction via `doc.get_toc()` + AI fallback. Chapter splitting by page range at lines 50-90.
- `backend/app/services/material_organizer.py` — `_extract_text_from_document()` at 78-120 (REUSE). `classify_material()` at 122-180 — DeepSeek JSON mode pattern.
- `backend/app/services/deepseek_provider.py` — `chat()` with JSON mode at lines 46-80.
- `backend/app/services/ai_router.py` — `get_json_response()` for structured DeepSeek output.
- `backend/app/models/description_schema.py` — Pydantic model pattern to follow.
- `frontend/src/pages/BookshelfPage.tsx` — 655 lines, 20+ useState. Course Preview "TBD" panel at line 477. Upload polling at 86-109. Progress indicator at 470-500.
- `frontend/src/styles/theme.css` — CSS variables source of truth.
- `frontend/src/api/courses.ts` — Frontend API client pattern to follow.

### Architecture Constraints (NON-NEGOTIABLE)
- NO migration framework (no Alembic, SQLAlchemy ORM)
- NO PRAGMA foreign_keys — cascade delete is application-level
- NO WebSocket/SSE — keep polling pattern (2s interval)
- NO global state management (useState only, no Redux/Zustand)
- NO new pages/routes — all UI in existing Course Preview panel
- UUID primary keys (TEXT) for all tables
- courses.id is TEXT — ALL FK columns referencing it must be TEXT, never INTEGER
- `INSERT OR IGNORE` pattern for idempotent inserts
- Try/except for ALTER TABLE migrations

### Current Pipeline State
- Single atomic background task — cannot pause
- `_job_status` in-memory dict — not persistent
- MinerU: `start_page_id`/`end_page_id` exist but NEVER tested with non-default values
- MinerU content type vocabulary UNKNOWN (spike Task 1 will document)

### Testing Patterns
- Backend: `pytest.fixture` with `tmp_path`, `await store.initialize()`, `AsyncMock` for DeepSeek
- Frontend: `vi.mock()` for API modules, `waitFor()`, `screen.findByText()`, `userEvent`
- Router tests: `httpx.AsyncClient` with `app` from `test_courses.py`

## [2026-02-28] Task: 2 — Schema v2 Complete

### Implementation Summary
- **TDD Approach**: Wrote 12 tests first (all failed), then implemented schema + 9 methods to make them pass
- **Schema Migrations**: Added `_migrate_v2()` method called from `initialize()` — fully idempotent
- **New Tables**: `sections`, `extracted_content`, `material_summaries` — all use TEXT PKs (UUID)
- **New Columns**: `chapters.extraction_status` (default 'pending'), `textbooks.pipeline_status` (default 'uploaded')
- **9 New Methods**:
  1. `create_section(section_data: dict) -> str` — INSERT, return id
  2. `get_sections_for_chapter(chapter_id: str) -> list[dict]` — SELECT by chapter_id
  3. `create_extracted_content(content_data: dict) -> str` — INSERT, return id
  4. `get_extracted_content_for_chapter(chapter_id: str) -> list[dict]` — SELECT by chapter_id
  5. `create_material_summary(summary_data: dict) -> str` — INSERT OR UPDATE (returns same id on update)
  6. `get_material_summary(material_id: str) -> dict | None` — SELECT by material_id
  7. `update_chapter_extraction_status(chapter_id: str, status: str) -> None` — UPDATE
  8. `update_textbook_pipeline_status(textbook_id: str, status: str) -> None` — UPDATE
  9. `get_chapters_by_extraction_status(textbook_id: str, status: str) -> list[dict]` — SELECT by textbook_id + status

### Key Patterns Applied
- **Idempotency**: All ALTER TABLE wrapped in try/except (column already exists)
- **UUID Generation**: `str(uuid.uuid4())` for all new IDs
- **Row Factory**: `db.row_factory = aiosqlite.Row` for dict conversion
- **Parameterized Queries**: All `?` placeholders (no SQL injection)
- **Material Summary Upsert**: Checks if summary exists before insert — returns same ID on update

### Test Results
- **12/12 tests PASS** in `test_schema_v2.py`
- **10/10 tests PASS** in `test_courses_storage.py` (no regressions)
- **Idempotency verified**: `initialize()` called twice → no errors, all tables/columns present

### Gotchas Encountered
1. **Material Summary ID Consistency**: Initial implementation generated new UUID on each call. Fixed by checking if summary exists and returning existing ID on update.
2. **Math Library Auto-Creation**: Accidentally removed during refactor. Restored to prevent test failures.
3. **Row Factory Scope**: Must set `db.row_factory = aiosqlite.Row` inside each method's async context (not persistent across connections).

### Files Modified
- `backend/app/services/storage.py` — Added MIGRATE_V2_SQL, _migrate_v2() method, 9 new methods
- `backend/tests/test_schema_v2.py` — Created with 12 comprehensive tests

### Evidence Files
- `.sisyphus/evidence/task-2-schema-tests.txt` — All 12 tests PASS
- `.sisyphus/evidence/task-2-idempotent.txt` — Idempotency verified

## [2026-02-28] Task: 1 — MinerU Spike Results

### Page Range Params
- **WORK**: YES — `start_page_id` and `end_page_id` correctly limit extraction.
- **IMPORTANT**: Output `page_idx` is REBASED to 0 (relative to extracted range). If you extract pages 22-35, output page_idx = 0-13. Caller must add `start_page_id` to get original page numbers.
- `end_page_id` is INCLUSIVE. Pages 22-35 = 14 pages (not 13).

### Content Type Vocabulary (5 types)
1. `text` — paragraphs, headings. Keys: type, text, text_level, bbox, page_idx
2. `equation` — LaTeX math. Keys: type, text, text_format="latex", img_path, bbox, page_idx
3. `image` — figures/diagrams. Keys: type, img_path, image_caption (list), image_footnote (list), bbox, page_idx
4. `table` — tables. Keys: type, text, img_path, bbox, page_idx
5. `discarded` — headers/footers/page numbers. SKIP these.

### Type Mapping to ContentType Enum
- `text` → ContentType.text
- `equation` → ContentType.equation
- `image` → ContentType.figure (NOTE: MinerU uses "image", our enum uses "figure")
- `table` → ContentType.table
- `discarded` → SKIP (do not store)

### Performance
- First call: ~57s for 14 pages (includes 22s model init)
- Subsequent calls: Model re-initializes each time (~22s overhead)
- Recommendation for Task 7: Batch all selected chapters into SINGLE MinerU call covering widest page range. Then split output by page_idx ranges per chapter.

### Multi-Call Safety
- No conflicts across 3 sequential calls with different page ranges
- Each call uses `tempfile.mkdtemp()` for unique temp dirs

### Key Decisions for Task 7
- Must add `start_page_id` offset to every entry's `page_idx` to get original page numbers
- Map MinerU "image" type to our "figure" ContentType
- Filter out "discarded" entries before storing
- Batch contiguous chapters for efficiency (model init is expensive)
