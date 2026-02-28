# Content Pipeline Redesign

## TL;DR

> **Quick Summary**: Replace the current automatic whole-book processing pipeline with a selective, course-material-informed pipeline. Textbook imports pause after TOC extraction for user verification. Course materials get DeepSeek-powered summaries that drive relevance matching against textbook chapters. MinerU extracts only selected chapters, storing tables/figures/equations as separate typed records. Remaining chapters can be extracted later via manual trigger.
> 
> **Deliverables**:
> - Selective per-chapter MinerU extraction with structured content storage (tables, figures, equations as separate DB records + files)
> - Course material summarization via DeepSeek (persistent summaries per material)
> - Relevance matching engine (course material topics ↔ textbook chapters)
> - Multi-phase pipeline with persistent state machine (replaces single background task)
> - Chapter verification UI inline on Course Preview panel
> - Manual "Extract remaining chapters" deferred extraction trigger
> - 2-level TOC hierarchy (chapters + sections)
> - Schema migrations for all new tables and columns
> - Full TDD test suite (pytest + vitest)
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: Task 1 (MinerU spike) → Task 2 (Schema) → Task 4 (Pipeline state machine) → Task 7 (Selective extractor) → Task 9 (Import pipeline rewrite) → Task 14 (Chapter verification UI) → F1–F4

---

## Context

### Original Request
User provided a flowchart showing a redesigned content processing pipeline with two parallel paths:
1. **Textbook path**: Import → TOC scan → relevance suggestions (informed by course materials) → user verification → selective MinerU extraction → DeepSeek descriptions
2. **Course material path**: Import → DeepSeek summarization → feeds into relevance matching + future learning features

Key user quotes:
- "DeepSeek should be primarily used to summarise content as well as search for content relevance"
- "The content extracted from MinerU such as tables figures equations should be stored in a way that's really easily accessible"
- "The content extracted from MinerU should also be categorized by chapters and subchapters listed in TOC"

### Interview Summary
**Key Discussions**:
- **User verification UX**: Inline on Course Preview panel (toggle chapters on/off), not a modal or separate page
- **Content accessibility**: Both files + DB records. Foundation for future clickable derivations in DeepSeek chat, content search in Desk UI
- **Downstream use cases**: Tutorial guidance, question generation, skills database, study materials — ALL explicitly OUT of this plan's scope (future plans building on this foundation)
- **Subchapter depth**: 2 levels (chapter + section), not full TOC depth
- **Content persistence**: Store all generated content persistently (summaries, descriptions, extracted content)
- **Deferred extraction**: Manual button only, no auto-background processing
- **Textbook-first import**: Full TOC + basic processing even without course materials, skip relevance matching
- **DeepSeek budget**: No constraints
- **Test strategy**: TDD (RED → GREEN → REFACTOR)

**Research Findings**:
- DeepSeek FULLY integrated — `deepseek_provider.py`, `ai_router.py`, chat/streaming/JSON mode
- MinerU FULLY integrated — `mineru_parser.py` with `start_page_id`/`end_page_id` params (but NEVER tested with non-default values)
- TOC already extracted via PyMuPDF `doc.get_toc()` + AI fallback via DeepSeek
- Current pipeline is a SINGLE atomic background task — cannot pause for user verification
- `_job_status` is in-memory dict — won't survive browser close or long verification pauses
- `BookshelfPage.tsx` is 655 lines with 20+ useState hooks — needs component extraction before adding more
- Course Preview "TBD" panel at line 477 is natural slot for chapter verification
- `material_organizer.py` classifies but does NOT summarize content
- No content type separation — MinerU output merged into text blobs

### Metis Review
**Identified Gaps** (addressed):
- **MinerU page-range extraction is untested**: Added spike task (Task 1) as hard blocker for all extraction work
- **MinerU content type vocabulary unknown**: Included in spike task — must catalog all `type` values from real output
- **Pipeline architecture mismatch**: Current single-background-task can't pause. Planned full replacement with persistent state machine (Task 4)
- **BookshelfPage bloat**: Component extraction (Task 12) must precede chapter verification UI (Task 14)
- **Manual migrations fragility**: Grouped all schema changes in single idempotent `_migrate_v2()` method (Task 2)
- **Retroactive relevance matching complexity**: Scoped as explicit task (Task 8) triggered only from material upload endpoint
- **Section extraction unreliability**: Made sections optional — degrade gracefully to chapter-only if TOC lacks level-2 entries
- **10 edge cases identified**: All addressed in relevant task QA scenarios

---

## Work Objectives

### Core Objective
Replace the automatic whole-book processing pipeline with a selective, multi-phase, course-material-informed pipeline that pauses for user verification, extracts only relevant chapters via MinerU, stores content as typed structured records, and supports deferred extraction of remaining chapters.

### Concrete Deliverables
- `backend/app/services/pipeline_orchestrator.py` — Multi-phase pipeline state machine
- `backend/app/services/material_summarizer.py` — DeepSeek-powered material summarization
- `backend/app/services/relevance_matcher.py` — Course material ↔ textbook chapter matching
- `backend/app/services/content_extractor.py` — MinerU-based selective per-chapter extraction with typed content separation
- Modified `backend/app/services/storage.py` — New tables + methods for sections, extracted content, summaries, pipeline state
- Modified `backend/app/routers/textbooks.py` — Rewritten import flow, new verification/extraction endpoints
- Modified `backend/app/routers/university_materials.py` — Trigger summarization + retroactive matching on upload
- New `frontend/src/components/CoursePreviewView.tsx` — Extracted from BookshelfPage
- New `frontend/src/components/ChapterVerification.tsx` — Toggle list for chapter selection
- Modified `frontend/src/pages/BookshelfPage.tsx` — Use extracted components, new pipeline states
- Full pytest + vitest test suites in TDD style

### Definition of Done
- [ ] `pytest backend/tests/ -v` → ALL PASS (including new tests)
- [ ] `bun test frontend/src/__tests__/ --run` → ALL PASS (including new tests)
- [ ] `npx tsc --noEmit` → 0 errors
- [ ] Textbook import pauses after TOC extraction, shows chapters in Course Preview
- [ ] User can toggle chapters and confirm selection
- [ ] Only selected chapters get MinerU extraction
- [ ] Extracted tables/figures/equations stored as separate DB records with files
- [ ] Course material upload triggers DeepSeek summarization
- [ ] Adding materials to a course with textbooks triggers retroactive relevance matching
- [ ] "Extract remaining" button triggers deferred extraction for non-selected chapters
- [ ] 2-level hierarchy (chapters + sections) stored in DB

### Must Have
- Persistent pipeline state in DB (not in-memory dict)
- Per-chapter extraction status tracking
- Structured content storage (tables, figures, equations as separate typed records)
- Course material summaries stored persistently
- Relevance matching between material summaries and chapter topics
- Chapter verification UI (toggle list in Course Preview)
- Manual deferred extraction trigger
- Textbook-first import works without course materials (skip relevance)
- Retroactive relevance matching when materials added to course with textbooks
- All new schema changes idempotent (safe to run twice)
- TDD: tests written before implementation for all new code

### Must NOT Have (Guardrails)
- **No content viewer/browser UI** for extracted tables/figures/equations (storage only in this plan)
- **No skills database or skill extraction** (future plan)
- **No question generation or tutorial walkthroughs** (future plan)
- **No clickable derivations in DeepSeek chat** (future plan — Desk UI)
- **No content search bar in Desk UI** (future plan)
- **No vector/embedding storage** (future plan)
- **No migration framework** (no Alembic, no SQLAlchemy ORM) — keep manual idempotent SQL
- **No WebSocket/SSE** — keep existing polling pattern for progress
- **No new pages/routes** — all UI in existing Course Preview panel
- **No chapter previews, drag-and-drop, inline descriptions in verification UI** — toggle + relevance badge only
- **No automatic background deferred extraction** — manual button only
- **No DeskPage or conversation feature modifications**
- **No per-slide summarization** — one DeepSeek call per material document
- **No global state management** (no Redux/Zustand) — keep useState pattern

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.
> Acceptance criteria requiring "user manually tests/confirms" are FORBIDDEN.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: TDD (RED → GREEN → REFACTOR)
- **Framework**: pytest (backend), vitest/bun test (frontend)
- **TDD flow**: Each task writes failing test → implements to pass → refactors

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Backend API**: Use Bash (curl) — Send requests, assert status + response fields
- **Backend Services**: Use Bash (pytest) — Import, call functions, compare output
- **Frontend UI**: Use Playwright (playwright skill) — Navigate, interact, assert DOM, screenshot
- **Schema**: Use Bash (pytest) — Run migrations twice, verify idempotency

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — spike + schema + types):
├── Task 1: MinerU spike — test page-range extraction + content type vocabulary [deep]
├── Task 2: Schema migrations — new tables + columns [quick]
├── Task 3: Pydantic models + TypeScript types [quick]

Wave 2 (Core services — MAX PARALLEL after Wave 1):
├── Task 4: Pipeline state machine + orchestrator (depends: 2) [deep]
├── Task 5: Material summarizer service (depends: 2, 3) [unspecified-high]
├── Task 6: Relevance matcher service (depends: 2, 3) [unspecified-high]
├── Task 7: Selective content extractor service (depends: 1, 2, 3) [deep]
├── Task 8: Retroactive matching trigger (depends: 5, 6) [unspecified-high]

Wave 3 (API + Frontend — integration):
├── Task 9: Rewrite textbook import API + pipeline integration (depends: 4, 7) [deep]
├── Task 10: Chapter verification + extraction API endpoints (depends: 4, 7) [unspecified-high]
├── Task 11: Material upload API — summarization + retroactive matching (depends: 5, 8) [unspecified-high]
├── Task 12: Extract CoursePreviewView component from BookshelfPage (depends: none — can start Wave 2) [quick]
├── Task 13: Frontend API client updates (depends: 10, 11) [quick]

Wave 4 (UI + Integration):
├── Task 14: Chapter verification UI component (depends: 12, 13) [visual-engineering]
├── Task 15: Pipeline progress + deferred extraction UI (depends: 12, 13, 9) [visual-engineering]
├── Task 16: Integration testing — full pipeline end-to-end (depends: 9, 10, 11, 14, 15) [deep]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high + playwright)
├── Task F4: Scope fidelity check (deep)

Critical Path: Task 1 → Task 2 → Task 4 → Task 7 → Task 9 → Task 14 → Task 16 → F1–F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 5 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 7 | 1 |
| 2 | — | 4, 5, 6, 7, 8 | 1 |
| 3 | — | 5, 6, 7 | 1 |
| 4 | 2 | 9, 10 | 2 |
| 5 | 2, 3 | 8, 11 | 2 |
| 6 | 2, 3 | 8 | 2 |
| 7 | 1, 2, 3 | 9, 10 | 2 |
| 8 | 5, 6 | 11 | 2 |
| 9 | 4, 7 | 15, 16 | 3 |
| 10 | 4, 7 | 13, 16 | 3 |
| 11 | 5, 8 | 13, 16 | 3 |
| 12 | — | 14, 15 | 3 (can start in Wave 2) |
| 13 | 10, 11 | 14, 15 | 3 |
| 14 | 12, 13 | 16 | 4 |
| 15 | 12, 13, 9 | 16 | 4 |
| 16 | 9, 10, 11, 14, 15 | F1–F4 | 4 |
| F1–F4 | 16 | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 → `deep`, T2 → `quick`, T3 → `quick`
- **Wave 2**: 5 tasks — T4 → `deep`, T5 → `unspecified-high`, T6 → `unspecified-high`, T7 → `deep`, T8 → `unspecified-high`
- **Wave 3**: 5 tasks — T9 → `deep`, T10 → `unspecified-high`, T11 → `unspecified-high`, T12 → `quick`, T13 → `quick`
- **Wave 4**: 3 tasks — T14 → `visual-engineering`, T15 → `visual-engineering`, T16 → `deep`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high` + playwright, F4 → `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.
> **A task WITHOUT QA Scenarios is INCOMPLETE. No exceptions.**
> **TDD: Every task writes failing tests FIRST, then implements to pass.**

### Wave 1 — Foundation (spike + schema + types)

- [x] 1. MinerU Spike — Test Page-Range Extraction + Content Type Vocabulary

  **What to do**:
  - **RED**: Write `backend/tests/test_mineru_spike.py` with tests:
    - `test_page_range_extraction()`: Call `do_parse()` with `start_page_id=10, end_page_id=20` on test PDF → assert output JSON contains entries only from pages 10-20
    - `test_content_type_vocabulary()`: Parse a real PDF chapter → catalog all `type` values from `document_content_list.json` → assert at least 3 distinct types exist (text + 2 others)
    - `test_multiple_sequential_calls()`: Call `do_parse()` 3 times with different page ranges → assert no conflicts (temp dirs, output quality)
  - **GREEN**: Run the tests against MinerU's actual `do_parse()` function from `mineru_parser.py`
  - If `start_page_id`/`end_page_id` don't work as expected → document the actual behavior and propose alternative (e.g., extract whole book once, split output by page)
  - Create `backend/tests/fixtures/spike_results.json` documenting all discovered content types with examples
  - **REFACTOR**: Clean up test fixtures, ensure reproducibility

  **Must NOT do**:
  - Do NOT modify `mineru_parser.py` yet — this is a READ-ONLY investigation
  - Do NOT build any production services — spike only
  - Do NOT assume content types without evidence

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Exploratory spike requiring investigation, debugging, and documentation of unknown behavior
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 2, 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 7 (selective content extractor depends on knowing MinerU capabilities)
  - **Blocked By**: None — can start immediately

  **References**:

  **Pattern References**:
  - `backend/app/services/mineru_parser.py:46-84` — `do_parse()` function with `start_page_id` and `end_page_id` parameters (lines 50-51). Currently hardcoded to `start_page_id=0, end_page_id=None`. This is the function to test.
  - `backend/app/services/mineru_parser.py:67` — Content iteration loop that checks `entry.get("type") == "discarded"`. Need to discover what OTHER type values exist.
  - `backend/app/services/mineru_parser.py:16-17` — Temp directory management. Need to verify multiple calls don't conflict.

  **API/Type References**:
  - `backend/app/services/mineru_parser.py:50-51` — `start_page_id=0, end_page_id=None` parameters to `do_parse()`

  **Test References**:
  - `backend/tests/test_pdf_parser.py` — Existing test pattern using `tmp_path` fixture and real PDFs. Follow this for the spike.

  **External References**:
  - MinerU GitHub docs for `do_parse()` parameter semantics

  **WHY Each Reference Matters**:
  - `mineru_parser.py:46-84`: This is THE function being spiked. Must understand its full signature and behavior.
  - `mineru_parser.py:67`: The type check logic — discovering what types exist beyond "discarded" directly determines how we design the content storage schema.
  - `test_pdf_parser.py`: Proves there's a test PDF available and shows the testing pattern to follow.

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_mineru_spike.py -v` → ALL PASS
  - [ ] `backend/tests/fixtures/spike_results.json` exists with documented content types
  - [ ] Spike results include: whether page-range params work, list of all content types with examples, performance notes for multiple calls

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Page-range extraction produces correct output
    Tool: Bash (pytest)
    Preconditions: Test PDF exists at backend/tests/fixtures/ (or any available PDF)
    Steps:
      1. Run: pytest backend/tests/test_mineru_spike.py::test_page_range_extraction -v
      2. Assert: test PASSES
      3. Verify output JSON only contains entries from specified page range
    Expected Result: Test passes, confirming start_page_id/end_page_id work correctly
    Failure Indicators: Test fails, OR output contains entries from outside specified range
    Evidence: .sisyphus/evidence/task-1-page-range-spike.txt

  Scenario: Content type vocabulary is documented
    Tool: Bash (pytest + file read)
    Preconditions: Spike test has run
    Steps:
      1. Run: pytest backend/tests/test_mineru_spike.py::test_content_type_vocabulary -v
      2. Read: backend/tests/fixtures/spike_results.json
      3. Assert: JSON contains key "content_types" with at least 3 entries
    Expected Result: Documented types include at minimum: text, table/image/equation variants
    Failure Indicators: Fewer than 3 types, or types don't include structured content
    Evidence: .sisyphus/evidence/task-1-content-types.json

  Scenario: Multiple MinerU calls don't conflict
    Tool: Bash (pytest)
    Preconditions: Test PDF available
    Steps:
      1. Run: pytest backend/tests/test_mineru_spike.py::test_multiple_sequential_calls -v
      2. Assert: all 3 calls succeed without temp dir conflicts
    Expected Result: All 3 extractions complete independently
    Failure Indicators: Any call fails with file/directory error, or output is corrupted
    Evidence: .sisyphus/evidence/task-1-multi-call.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-page-range-spike.txt — pytest output showing page-range test result
  - [ ] task-1-content-types.json — copy of spike_results.json with all discovered types
  - [ ] task-1-multi-call.txt — pytest output for sequential call test

  **Commit**: YES (groups with Wave 1)
  - Message: `test(backend): spike MinerU page-range extraction and content types`
  - Files: `backend/tests/test_mineru_spike.py`, `backend/tests/fixtures/spike_results.json`
  - Pre-commit: `pytest backend/tests/test_mineru_spike.py -v`

- [x] 2. Schema Migrations — New Tables + Columns

  **What to do**:
  - **RED**: Write `backend/tests/test_schema_v2.py` with tests:
    - `test_sections_table_exists()`: After `initialize()`, query `sections` table
    - `test_extracted_content_table_exists()`: After `initialize()`, query `extracted_content` table
    - `test_material_summaries_table_exists()`: After `initialize()`, query `material_summaries` table
    - `test_chapters_extraction_status_column()`: Insert chapter with `extraction_status="pending"` → read back
    - `test_textbooks_pipeline_status_column()`: Insert textbook with `pipeline_status="uploaded"` → read back
    - `test_initialize_twice_is_idempotent()`: Call `initialize()` twice → no errors on second call
    - `test_sections_linked_to_chapter()`: Insert section with valid `chapter_id` FK → succeeds
    - `test_extracted_content_linked_to_chapter()`: Insert content with valid `chapter_id` → succeeds
  - **GREEN**: Implement in `storage.py`:
    - Add `_migrate_v2()` method called from `initialize()`, wrapping all new schema in try/except for idempotency
    - New table `sections`: `id TEXT PK, chapter_id TEXT, section_number INT, title TEXT, page_start INT, page_end INT`
    - New table `extracted_content`: `id TEXT PK, chapter_id TEXT, content_type TEXT (table|figure|equation|text), title TEXT, content TEXT, file_path TEXT, page_number INT, order_index INT`
    - New table `material_summaries`: `id TEXT PK, material_id TEXT, course_id TEXT, summary_json TEXT, created_at TIMESTAMP`
    - New column on `chapters`: `extraction_status TEXT DEFAULT 'pending'` (values: pending, selected, extracting, extracted, deferred, error)
    - New column on `textbooks`: `pipeline_status TEXT DEFAULT 'uploaded'` (values: uploaded, toc_extracted, awaiting_verification, extracting, partially_extracted, fully_extracted, error)
    - New `MetadataStore` methods: `create_section()`, `get_sections_for_chapter()`, `create_extracted_content()`, `get_extracted_content_for_chapter()`, `create_material_summary()`, `get_material_summary()`, `update_chapter_extraction_status()`, `update_textbook_pipeline_status()`, `get_chapters_by_extraction_status()`
  - **REFACTOR**: Ensure all methods follow existing patterns in `storage.py`

  **Must NOT do**:
  - Do NOT introduce Alembic or any migration framework
  - Do NOT modify existing table schemas beyond adding new columns
  - Do NOT enable `PRAGMA foreign_keys` — cascade delete is application-level
  - Do NOT drop or rename existing columns

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Schema changes follow established patterns in storage.py — well-defined, repetitive work
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 4, 5, 6, 7, 8 (all services need the new tables)
  - **Blocked By**: None — can start immediately

  **References**:

  **Pattern References**:
  - `backend/app/services/storage.py:14-72` — Existing table creation pattern in `initialize()`. Follow exact style: `CREATE TABLE IF NOT EXISTS`, UUID primary keys, TEXT foreign keys.
  - `backend/app/services/storage.py:74-79` — Existing migration pattern using `try/except` for idempotent `ALTER TABLE`. Follow this exact pattern for new columns.
  - `backend/app/services/storage.py:81-160` — Existing CRUD methods (e.g., `create_course()`, `get_textbook()`). Follow this pattern for new methods: `async def`, use `self.db`, parameterized queries.

  **API/Type References**:
  - `backend/app/services/storage.py:26-35` — Current `chapters` table schema (what to add `extraction_status` to)
  - `backend/app/services/storage.py:53-60` — Current `university_materials` table schema (FK target for `material_summaries`)

  **Test References**:
  - `backend/tests/test_courses_storage.py` — Existing MetadataStore test pattern: `pytest.fixture` with `tmp_path`, `await store.initialize()`, direct method calls + assertions

  **WHY Each Reference Matters**:
  - `storage.py:14-72`: Every new table must follow this exact CREATE TABLE style to maintain consistency
  - `storage.py:74-79`: The try/except ALTER TABLE pattern is the ONLY accepted migration approach — must follow exactly
  - `storage.py:81-160`: New CRUD methods must match existing method signatures and patterns (async, parameterized SQL)
  - `test_courses_storage.py`: The testing fixture pattern (tmp_path, initialize) must be reused for new table tests

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_schema_v2.py -v` → ALL PASS (8 tests)
  - [ ] `initialize()` called twice in sequence → no errors
  - [ ] All new columns have correct defaults

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All new tables created successfully
    Tool: Bash (pytest)
    Preconditions: Clean test database (tmp_path fixture)
    Steps:
      1. Run: pytest backend/tests/test_schema_v2.py -v
      2. Assert: 8 tests pass
    Expected Result: All tables exist, all columns present, FK relationships work
    Failure Indicators: Any test fails, table missing, column type wrong
    Evidence: .sisyphus/evidence/task-2-schema-tests.txt

  Scenario: Migration idempotency
    Tool: Bash (pytest)
    Preconditions: None
    Steps:
      1. Run: pytest backend/tests/test_schema_v2.py::test_initialize_twice_is_idempotent -v
      2. Assert: PASSES with no exceptions
    Expected Result: Second initialize() call completes without errors
    Failure Indicators: SQLite error about existing table/column
    Evidence: .sisyphus/evidence/task-2-idempotent.txt
  ```

  **Evidence to Capture:**
  - [ ] task-2-schema-tests.txt — pytest output for all schema tests
  - [ ] task-2-idempotent.txt — pytest output for idempotency test

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(backend): add v2 schema migrations for content pipeline`
  - Files: `backend/app/services/storage.py`, `backend/tests/test_schema_v2.py`
  - Pre-commit: `pytest backend/tests/test_schema_v2.py -v`

- [x] 3. Pydantic Models + TypeScript Types

  **What to do**:
  - **RED**: Write test assertions in `backend/tests/test_pipeline_models.py`:
    - `test_section_model_validation()`: Create Section with valid/invalid data
    - `test_extracted_content_model()`: Create ExtractedContent with all content_type enum values
    - `test_material_summary_model()`: Create MaterialSummary with nested topic list
    - `test_pipeline_status_enum()`: Verify all pipeline status values are valid
    - `test_chapter_extraction_status_enum()`: Verify all extraction status values
    - `test_relevance_result_model()`: Create RelevanceResult with score + reasoning
  - **GREEN**: Implement in `backend/app/models/pipeline_models.py`:
    - `PipelineStatus` enum: uploaded, toc_extracted, awaiting_verification, extracting, partially_extracted, fully_extracted, error
    - `ExtractionStatus` enum: pending, selected, extracting, extracted, deferred, error
    - `ContentType` enum: table, figure, equation, text
    - `Section` model: id, chapter_id, section_number, title, page_start, page_end
    - `ExtractedContent` model: id, chapter_id, content_type, title, content, file_path, page_number, order_index
    - `MaterialSummary` model: id, material_id, course_id, topics (list of {title, description, slide_range}), raw_summary, created_at
    - `RelevanceResult` model: chapter_id, chapter_title, relevance_score (0-1), matched_topics (list), reasoning
    - `ChapterVerificationRequest` model: selected_chapter_ids (list of str)
    - `ChapterWithStatus` model: id, title, chapter_number, page_start, page_end, extraction_status, relevance_score (optional), matched_topics (optional)
  - Implement TypeScript types in `frontend/src/types/pipeline.ts`:
    - Mirror all relevant models for frontend consumption
    - `ChapterWithStatus`, `RelevanceResult`, `PipelineStatus`, `ExtractionStatus`
  - **REFACTOR**: Ensure consistency with existing models in `description_schema.py` and `ai_models.py`

  **Must NOT do**:
  - Do NOT create frontend API client functions yet (Task 13)
  - Do NOT modify existing model files — create new `pipeline_models.py`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Type definitions and enums — straightforward, well-defined work
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 2)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 5, 6, 7 (services need the type definitions)
  - **Blocked By**: None — can start immediately

  **References**:

  **Pattern References**:
  - `backend/app/models/description_schema.py` — Existing Pydantic model pattern: BaseModel subclass, typed fields, Optional annotations. Follow this exact style.
  - `backend/app/models/ai_models.py` — More complex models: ConceptExtraction, ClassifiedMatch, PracticeProblems. Shows how to structure nested models with lists.

  **API/Type References**:
  - `backend/app/services/storage.py:26-35` — Chapter table columns → `ChapterWithStatus` fields must match
  - `frontend/src/api/courses.ts` — Existing TypeScript API types. Follow this import/export pattern.
  - `frontend/src/api/textbooks.ts` — Existing frontend types for textbook data

  **WHY Each Reference Matters**:
  - `description_schema.py`: THE pattern for Pydantic models in this codebase — field style, Optional usage, etc.
  - `ai_models.py`: Shows nested model patterns needed for MaterialSummary's topics list
  - `courses.ts` + `textbooks.ts`: Frontend type patterns to match for consistency

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_pipeline_models.py -v` → ALL PASS (6 tests)
  - [ ] `npx tsc --noEmit` → 0 errors (TypeScript types compile)
  - [ ] All enum values match schema column defaults from Task 2

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All Pydantic models validate correctly
    Tool: Bash (pytest)
    Preconditions: None
    Steps:
      1. Run: pytest backend/tests/test_pipeline_models.py -v
      2. Assert: 6 tests pass
    Expected Result: All models accept valid data, reject invalid data
    Failure Indicators: Validation errors on valid data, or accepts invalid data
    Evidence: .sisyphus/evidence/task-3-model-tests.txt

  Scenario: TypeScript types compile cleanly
    Tool: Bash (tsc)
    Preconditions: frontend/src/types/pipeline.ts exists
    Steps:
      1. Run: npx tsc --noEmit
      2. Assert: exit code 0, no errors mentioning pipeline.ts
    Expected Result: Clean compilation
    Failure Indicators: Type errors in pipeline.ts
    Evidence: .sisyphus/evidence/task-3-tsc-check.txt
  ```

  **Evidence to Capture:**
  - [ ] task-3-model-tests.txt — pytest output
  - [ ] task-3-tsc-check.txt — tsc output

  **Commit**: YES (groups with Wave 1)
  - Message: `feat: add pipeline Pydantic models and TypeScript types`
  - Files: `backend/app/models/pipeline_models.py`, `backend/tests/test_pipeline_models.py`, `frontend/src/types/pipeline.ts`
  - Pre-commit: `pytest backend/tests/test_pipeline_models.py -v && npx tsc --noEmit`

### Wave 2 — Core Services (MAX PARALLEL after Wave 1)

- [x] 4. Pipeline State Machine + Orchestrator

  **What to do**:
  - **RED**: Write `backend/tests/test_pipeline_orchestrator.py` with tests:
    - `test_start_pipeline_sets_uploaded()`: New textbook → pipeline_status = "uploaded"
    - `test_toc_phase_transitions_to_toc_extracted()`: After TOC scan → pipeline_status = "toc_extracted"
    - `test_toc_phase_without_materials_skips_relevance()`: No materials in course → pipeline_status = "toc_extracted" (no relevance results)
    - `test_toc_phase_with_materials_includes_relevance()`: Materials exist → pipeline_status = "toc_extracted" + relevance results returned
    - `test_verification_transitions_to_awaiting()`: Status moves to "awaiting_verification" when chapters presented
    - `test_extraction_phase_starts_for_selected()`: After verification → selected chapters get extraction_status = "extracting", others = "deferred"
    - `test_extraction_complete_transitions()`: All selected chapters extracted → pipeline_status = "partially_extracted" or "fully_extracted"
    - `test_deferred_extraction_works()`: Manual trigger → deferred chapters get extraction_status = "extracting"
    - `test_error_handling_sets_error_status()`: Exception during any phase → pipeline_status = "error" with details
    - `test_pipeline_state_persists_across_restart()`: Status saved to DB → survives process restart
  - **GREEN**: Implement `backend/app/services/pipeline_orchestrator.py`:
    - `PipelineOrchestrator` class with methods for each phase:
      - `start_import(textbook_id, course_id, file_path)` → Saves PDF, creates textbook record, status = "uploaded"
      - `run_toc_phase(textbook_id)` → Extract TOC, split chapters, generate basic sections. If course has materials: run relevance matching. Set status = "toc_extracted"
      - `submit_verification(textbook_id, selected_chapter_ids)` → Mark selected chapters, set unselected to "deferred", set status = "awaiting_verification" → "extracting"
      - `run_extraction_phase(textbook_id, chapter_ids)` → MinerU extraction for selected chapters (background task), update status per chapter
      - `run_deferred_extraction(textbook_id, chapter_ids)` → Same as extraction but for previously deferred chapters (triggered by manual button)
      - `run_description_phase(textbook_id, chapter_ids)` → Generate DeepSeek descriptions for extracted chapters
    - Each method: update `pipeline_status` / `extraction_status` in DB, handle errors gracefully (set error status, don't crash)
    - Replace `_job_status` in-memory dict with DB-backed state via `storage.update_textbook_pipeline_status()`
  - **REFACTOR**: Extract common state transition logic, add logging

  **Must NOT do**:
  - Do NOT modify the existing `process_pdf_background()` yet — that's Task 9
  - Do NOT call MinerU directly — use the content extractor from Task 7
  - Do NOT call DeepSeek directly — use services from Tasks 5, 6
  - Orchestrator coordinates, does not implement extraction/summarization logic

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex state machine design with error handling, persistence, and multiple phases
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 6, 7, 8)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 9, 10 (API endpoints use the orchestrator)
  - **Blocked By**: Task 2 (needs schema for state persistence)

  **References**:

  **Pattern References**:
  - `backend/app/routers/textbooks.py:44-79` — Current `process_pdf_background()` — the function being REPLACED. Shows the current linear flow: save file → parse PDF → save chapters. Orchestrator must decompose this into phases.
  - `backend/app/routers/textbooks.py:15` — `_job_status` dict. This is what gets replaced with DB-backed state.
  - `backend/app/services/storage.py:81-160` — MetadataStore methods pattern. Orchestrator calls these for state updates.

  **API/Type References**:
  - `backend/app/models/pipeline_models.py` — (from Task 3) PipelineStatus enum, ExtractionStatus enum, ChapterWithStatus model

  **WHY Each Reference Matters**:
  - `textbooks.py:44-79`: Must understand the CURRENT flow to correctly decompose it into phases
  - `textbooks.py:15`: The `_job_status` dict is the anti-pattern being replaced — understand how it's used by the frontend polling
  - `storage.py`: Orchestrator is a coordinator that delegates all DB work to MetadataStore

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_pipeline_orchestrator.py -v` → ALL PASS (10 tests)
  - [ ] Pipeline state transitions correctly through all phases
  - [ ] Error in any phase sets status to "error" without crashing
  - [ ] State persists to DB (survives mock restart)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full pipeline state progression (happy path)
    Tool: Bash (pytest)
    Preconditions: Test database with schema v2 initialized
    Steps:
      1. Run: pytest backend/tests/test_pipeline_orchestrator.py -v -k "not error"
      2. Assert: All non-error tests pass
      3. Verify state transitions: uploaded → toc_extracted → awaiting_verification → extracting → partially_extracted
    Expected Result: All phases transition correctly
    Failure Indicators: Wrong status at any phase, DB not updated
    Evidence: .sisyphus/evidence/task-4-orchestrator-happy.txt

  Scenario: Error recovery sets error status
    Tool: Bash (pytest)
    Preconditions: Test database initialized
    Steps:
      1. Run: pytest backend/tests/test_pipeline_orchestrator.py::test_error_handling_sets_error_status -v
      2. Assert: PASSES — error status set, no unhandled exception
    Expected Result: pipeline_status = "error" in DB after exception
    Failure Indicators: Unhandled exception, or status not updated
    Evidence: .sisyphus/evidence/task-4-orchestrator-error.txt
  ```

  **Evidence to Capture:**
  - [ ] task-4-orchestrator-happy.txt
  - [ ] task-4-orchestrator-error.txt

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(backend): add pipeline orchestrator with persistent state machine`
  - Files: `backend/app/services/pipeline_orchestrator.py`, `backend/tests/test_pipeline_orchestrator.py`
  - Pre-commit: `pytest backend/tests/test_pipeline_orchestrator.py -v`

- [x] 5. Material Summarizer Service

  **What to do**:
  - **RED**: Write `backend/tests/test_material_summarizer.py` with tests:
    - `test_summarize_pdf_material()`: Mock DeepSeek → returns structured summary with topics
    - `test_summarize_pptx_material()`: Mock DeepSeek → handles slide-based content
    - `test_summary_stored_persistently()`: After summarization → summary exists in DB via MetadataStore
    - `test_empty_content_returns_error()`: No extractable text → returns graceful error (not crash)
    - `test_summary_format_has_topics()`: Summary JSON contains topics list with title + description + source_range
  - **GREEN**: Implement `backend/app/services/material_summarizer.py`:
    - `MaterialSummarizer` class:
      - `summarize(material_id, file_path, course_id)` → MaterialSummary
      - Extract text from file using `_extract_text_from_document()` pattern from `material_organizer.py`
      - Send to DeepSeek with prompt: "Summarize this course material. For each distinct topic, provide: topic title, description (2-3 sentences), and which pages/slides it covers. Return as JSON."
      - Parse DeepSeek response into `MaterialSummary` model
      - Save to DB via `store.create_material_summary()`
      - Handle empty/unreadable documents gracefully
  - **REFACTOR**: Extract shared text extraction utility if duplicating material_organizer.py logic

  **Must NOT do**:
  - Do NOT summarize per-slide (one call per document)
  - Do NOT modify `material_organizer.py` — create separate service
  - Do NOT integrate with upload endpoint yet (Task 11)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: DeepSeek integration with structured output parsing — moderate complexity
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 6, 7)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 8, 11 (retroactive matching + material upload API need summaries)
  - **Blocked By**: Tasks 2, 3 (needs schema + models)

  **References**:

  **Pattern References**:
  - `backend/app/services/material_organizer.py:78-120` — `_extract_text_from_document()` method. Shows how to extract text from PDF/PPTX/DOCX. Reuse this pattern (or import directly).
  - `backend/app/services/material_organizer.py:122-180` — `classify_material()` method. Shows the DeepSeek call pattern: build prompt, call `ai_router.get_json_response()`, parse result.
  - `backend/app/services/deepseek_provider.py:46-80` — `chat()` method with JSON mode. The actual API call pattern.

  **API/Type References**:
  - `backend/app/models/pipeline_models.py` — (from Task 3) MaterialSummary model
  - `backend/app/services/ai_router.py` — `get_json_response()` method for structured DeepSeek output

  **WHY Each Reference Matters**:
  - `material_organizer.py:78-120`: Text extraction logic already exists — DON'T reinvent, reuse or import
  - `material_organizer.py:122-180`: The DeepSeek structured output pattern to follow exactly
  - `deepseek_provider.py`: Understanding the actual API interface for error handling

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_material_summarizer.py -v` → ALL PASS (5 tests)
  - [ ] DeepSeek called with correct prompt structure
  - [ ] Summary persisted to DB with all required fields

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: PDF material produces valid summary
    Tool: Bash (pytest)
    Preconditions: Mock DeepSeek provider
    Steps:
      1. Run: pytest backend/tests/test_material_summarizer.py::test_summarize_pdf_material -v
      2. Assert: PASSES, summary has topics list with at least 1 entry
    Expected Result: Summary stored with topics, each having title + description
    Failure Indicators: Empty summary, missing topics, or DeepSeek not called
    Evidence: .sisyphus/evidence/task-5-summarizer-tests.txt

  Scenario: Unreadable document handled gracefully
    Tool: Bash (pytest)
    Preconditions: Material with no extractable text
    Steps:
      1. Run: pytest backend/tests/test_material_summarizer.py::test_empty_content_returns_error -v
      2. Assert: PASSES, returns error result (not exception)
    Expected Result: Graceful error response, no crash
    Failure Indicators: Unhandled exception
    Evidence: .sisyphus/evidence/task-5-summarizer-error.txt
  ```

  **Evidence to Capture:**
  - [ ] task-5-summarizer-tests.txt
  - [ ] task-5-summarizer-error.txt

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(backend): add material summarizer service with DeepSeek integration`
  - Files: `backend/app/services/material_summarizer.py`, `backend/tests/test_material_summarizer.py`
  - Pre-commit: `pytest backend/tests/test_material_summarizer.py -v`

- [x] 6. Relevance Matcher Service

  **What to do**:
  - **RED**: Write `backend/tests/test_relevance_matcher.py` with tests:
    - `test_match_chapters_to_summaries()`: Mock DeepSeek → returns relevance scores for each chapter
    - `test_no_materials_returns_empty()`: No material summaries → returns empty results (not error)
    - `test_relevance_scores_between_0_and_1()`: All scores in valid range
    - `test_chapters_ranked_by_relevance()`: Results sorted by score descending
    - `test_matched_topics_populated()`: Each result includes which material topics matched
  - **GREEN**: Implement `backend/app/services/relevance_matcher.py`:
    - `RelevanceMatcher` class:
      - `match_chapters(textbook_id, course_id)` → list[RelevanceResult]
      - Fetch all material summaries for the course via MetadataStore
      - Fetch all chapter titles + descriptions for the textbook
      - Build DeepSeek prompt: "Given these course material topics: [topics]. And these textbook chapters: [chapters]. Rate the relevance of each chapter to the course (0-1 score). Return JSON."
      - Parse response into list of `RelevanceResult`
      - Sort by relevance_score descending
      - Return results (caller decides what to do with them)
  - **REFACTOR**: Optimize prompt for token efficiency if needed

  **Must NOT do**:
  - Do NOT store relevance results in DB (they're computed on-demand during TOC phase)
  - Do NOT modify any existing services
  - Do NOT implement the chapter suggestion UI logic — just the matching engine

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: DeepSeek prompt engineering + structured JSON parsing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 5, 7)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 8 (retroactive matching uses this)
  - **Blocked By**: Tasks 2, 3 (needs schema + models)

  **References**:

  **Pattern References**:
  - `backend/app/services/description_generator.py:45-100` — DeepSeek structured output generation. Shows how to build prompts with textbook content and parse JSON responses.
  - `backend/app/services/material_organizer.py:122-180` — Another DeepSeek JSON mode call pattern. Shows classification prompt structure.

  **API/Type References**:
  - `backend/app/models/pipeline_models.py` — (from Task 3) RelevanceResult model
  - `backend/app/services/ai_router.py` — `get_json_response()` for structured output

  **WHY Each Reference Matters**:
  - `description_generator.py`: Shows the pattern for building prompts with chapter data — directly applicable
  - `material_organizer.py`: Shows classification-style DeepSeek prompts — relevance matching is similar

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_relevance_matcher.py -v` → ALL PASS (5 tests)
  - [ ] Results sorted by relevance score
  - [ ] Empty course materials handled gracefully

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Chapters matched against material topics
    Tool: Bash (pytest)
    Preconditions: Mock DeepSeek returns relevance scores
    Steps:
      1. Run: pytest backend/tests/test_relevance_matcher.py -v
      2. Assert: 5 tests pass
      3. Verify results contain chapter_id, score, matched_topics for each chapter
    Expected Result: All chapters scored, sorted by relevance
    Failure Indicators: Missing chapters, scores outside 0-1, unsorted results
    Evidence: .sisyphus/evidence/task-6-matcher-tests.txt

  Scenario: No materials returns empty (not error)
    Tool: Bash (pytest)
    Preconditions: Course with no material summaries
    Steps:
      1. Run: pytest backend/tests/test_relevance_matcher.py::test_no_materials_returns_empty -v
      2. Assert: PASSES, returns empty list
    Expected Result: Empty list returned, no DeepSeek call made
    Failure Indicators: Exception or DeepSeek called unnecessarily
    Evidence: .sisyphus/evidence/task-6-matcher-empty.txt
  ```

  **Evidence to Capture:**
  - [ ] task-6-matcher-tests.txt
  - [ ] task-6-matcher-empty.txt

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(backend): add relevance matcher service for course material-chapter matching`
  - Files: `backend/app/services/relevance_matcher.py`, `backend/tests/test_relevance_matcher.py`
  - Pre-commit: `pytest backend/tests/test_relevance_matcher.py -v`

- [x] 7. Selective Content Extractor Service

  **What to do**:
  - **RED**: Write `backend/tests/test_content_extractor.py` with tests:
    - `test_extract_single_chapter()`: MinerU called with correct page range → returns typed content list
    - `test_content_types_separated()`: Output contains separate entries for tables, figures, equations, text
    - `test_content_stored_in_db()`: Extracted content saved to `extracted_content` table with correct chapter_id
    - `test_content_files_created()`: Files saved to `data/textbooks/{id}/chapters/{num}/content/` directory
    - `test_batch_contiguous_chapters()`: Chapters with adjacent page ranges batched into single MinerU call
    - `test_partial_failure_marks_error()`: If extraction fails for one chapter → that chapter = "error", others succeed
    - `test_sections_created_from_toc()`: Level-2 TOC entries become section records linked to chapters
  - **GREEN**: Implement `backend/app/services/content_extractor.py`:
    - `ContentExtractor` class:
      - `extract_chapters(textbook_id, chapter_ids, pdf_path)` → list[ExtractedContent]
      - For each chapter: look up page_start/page_end from DB
      - Batch contiguous chapters into single MinerU call (optimization from spike)
      - Call MinerU's `do_parse()` with `start_page_id` and `end_page_id`
      - Parse `content_list.json` output: classify each entry by type (using vocabulary from spike)
      - Save each typed content item to `extracted_content` table
      - Save files to `data/textbooks/{id}/chapters/{num}/content/{type}_{index}.md`
      - Update `chapters.extraction_status` = "extracted" for each successful chapter
      - Handle per-chapter errors: mark failed chapter as "error", continue with others
    - `extract_sections(textbook_id, chapter_id, toc_entries)` → list[Section]
      - From level-2 TOC entries, create Section records linked to chapter
      - Calculate section page ranges from TOC
      - Gracefully handle missing level-2 entries (just skip, chapter works without sections)
  - **REFACTOR**: Apply content type mapping from spike results

  **Must NOT do**:
  - Do NOT modify `mineru_parser.py` — call `do_parse()` as-is with page range params
  - Do NOT build any content viewing/rendering logic
  - Do NOT extract content for unselected/deferred chapters

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex MinerU integration with batching, error handling, and content classification
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 5, 6)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 9, 10 (import pipeline + API endpoints use this)
  - **Blocked By**: Tasks 1 (spike results), 2 (schema), 3 (models)

  **References**:

  **Pattern References**:
  - `backend/app/services/mineru_parser.py:46-84` — `do_parse()` function. THE extraction function to call. Use `start_page_id` and `end_page_id` parameters validated in spike.
  - `backend/app/services/pdf_parser.py:50-90` — Current chapter splitting logic using TOC entries. Shows how page ranges are calculated from `doc.get_toc()` output. Reuse for section page range calculation.
  - `backend/tests/fixtures/spike_results.json` — (from Task 1) Content type vocabulary. Map each MinerU type to our ContentType enum.

  **API/Type References**:
  - `backend/app/models/pipeline_models.py` — (from Task 3) ExtractedContent, Section, ContentType enum
  - `backend/app/services/storage.py` — (from Task 2) `create_extracted_content()`, `create_section()` methods

  **Test References**:
  - `backend/tests/test_mineru_spike.py` — (from Task 1) Shows actual MinerU behavior for page-range extraction

  **WHY Each Reference Matters**:
  - `mineru_parser.py`: THE function being wrapped — must call correctly based on spike findings
  - `pdf_parser.py:50-90`: Page range calculation logic to reuse for section boundaries
  - `spike_results.json`: Content type mapping — determines how MinerU output is classified

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_content_extractor.py -v` → ALL PASS (7 tests)
  - [ ] Content types correctly separated (table, figure, equation, text)
  - [ ] Files created in correct directory structure
  - [ ] Partial failure handled gracefully

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Single chapter extraction with typed content separation
    Tool: Bash (pytest)
    Preconditions: Mock MinerU returns mixed content types, schema initialized
    Steps:
      1. Run: pytest backend/tests/test_content_extractor.py::test_content_types_separated -v
      2. Assert: PASSES, DB contains entries with distinct content_type values
    Expected Result: Tables, figures, equations, text stored as separate records
    Failure Indicators: All content lumped as one type, or types not matching spike vocabulary
    Evidence: .sisyphus/evidence/task-7-extractor-types.txt

  Scenario: Partial failure doesn't crash entire extraction
    Tool: Bash (pytest)
    Preconditions: Mock MinerU fails for one chapter but succeeds for others
    Steps:
      1. Run: pytest backend/tests/test_content_extractor.py::test_partial_failure_marks_error -v
      2. Assert: PASSES, failed chapter = "error" status, others = "extracted"
    Expected Result: Graceful per-chapter error handling
    Failure Indicators: Entire extraction fails, or error chapter not marked
    Evidence: .sisyphus/evidence/task-7-extractor-partial-fail.txt
  ```

  **Evidence to Capture:**
  - [ ] task-7-extractor-types.txt
  - [ ] task-7-extractor-partial-fail.txt

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(backend): add selective content extractor with typed content separation`
  - Files: `backend/app/services/content_extractor.py`, `backend/tests/test_content_extractor.py`
  - Pre-commit: `pytest backend/tests/test_content_extractor.py -v`

- [x] 8. Retroactive Matching Trigger

  **What to do**:
  - **RED**: Write `backend/tests/test_retroactive_matching.py` with tests:
    - `test_new_summary_triggers_matching()`: Material summarized → if textbooks exist in course → relevance re-calculated
    - `test_no_textbooks_skips_matching()`: Material summarized → no textbooks → no matching (no error)
    - `test_multiple_textbooks_all_matched()`: Course with 2 textbooks → both get relevance results
    - `test_matching_results_returned()`: After trigger → returns list of RelevanceResult per textbook
  - **GREEN**: Implement `backend/app/services/retroactive_matcher.py`:
    - `RetroactiveMatcher` class:
      - `on_material_summarized(course_id, material_summary)` → dict[textbook_id, list[RelevanceResult]]
      - Fetch all textbooks in the course that are in state `toc_extracted` or later
      - For each textbook: call `RelevanceMatcher.match_chapters(textbook_id, course_id)`
      - Return results keyed by textbook_id
      - If no textbooks: return empty dict, no error
  - **REFACTOR**: Ensure this is a thin coordinator, not duplicating relevance logic

  **Must NOT do**:
  - Do NOT implement event bus or pub/sub — direct function call from upload endpoint
  - Do NOT auto-trigger chapter re-extraction based on new relevance scores
  - Do NOT modify existing relevance matcher — just call it

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Coordination logic with multiple service calls
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 7 — but after 5, 6)
  - **Parallel Group**: Wave 2 (late start — depends on 5, 6)
  - **Blocks**: Task 11 (material upload API calls this)
  - **Blocked By**: Tasks 5, 6 (needs summarizer + matcher)

  **References**:

  **Pattern References**:
  - `backend/app/services/relevance_matcher.py` — (from Task 6) The matcher to call. Retroactive matcher is a thin wrapper.
  - `backend/app/services/material_summarizer.py` — (from Task 5) Produces the summaries that trigger retroactive matching.

  **API/Type References**:
  - `backend/app/models/pipeline_models.py` — RelevanceResult model
  - `backend/app/services/storage.py` — `get_textbooks_for_course()` to find textbooks to match against

  **WHY Each Reference Matters**:
  - `relevance_matcher.py`: THE service being delegated to — retroactive matcher just orchestrates calls to it
  - `storage.py`: Need to know how to query textbooks by course to find matching targets

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_retroactive_matching.py -v` → ALL PASS (4 tests)
  - [ ] No textbooks → graceful empty return
  - [ ] Multiple textbooks all processed

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Material upload triggers matching for existing textbooks
    Tool: Bash (pytest)
    Preconditions: Course with 1 textbook (toc_extracted state) + new material summary
    Steps:
      1. Run: pytest backend/tests/test_retroactive_matching.py::test_new_summary_triggers_matching -v
      2. Assert: PASSES, relevance results returned for the textbook
    Expected Result: Textbook chapters scored against new material topics
    Failure Indicators: No matching triggered, or error during matching
    Evidence: .sisyphus/evidence/task-8-retroactive-tests.txt

  Scenario: Empty course (no textbooks) handled gracefully
    Tool: Bash (pytest)
    Preconditions: Course with no textbooks, new material uploaded
    Steps:
      1. Run: pytest backend/tests/test_retroactive_matching.py::test_no_textbooks_skips_matching -v
      2. Assert: PASSES, returns empty dict
    Expected Result: No error, no unnecessary API calls
    Failure Indicators: Exception thrown, or DeepSeek called with no chapters
    Evidence: .sisyphus/evidence/task-8-retroactive-empty.txt
  ```

  **Evidence to Capture:**
  - [ ] task-8-retroactive-tests.txt
  - [ ] task-8-retroactive-empty.txt

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(backend): add retroactive matching trigger for material uploads`
  - Files: `backend/app/services/retroactive_matcher.py`, `backend/tests/test_retroactive_matching.py`
  - Pre-commit: `pytest backend/tests/test_retroactive_matching.py -v`

### Wave 3 — API + Frontend (integration)

- [ ] 9. Rewrite Textbook Import API + Pipeline Integration

  **What to do**:
  - **RED**: Write `backend/tests/test_import_pipeline.py` with tests:
    - `test_import_starts_pipeline()`: POST /import → returns textbook_id + status "uploaded", background task starts
    - `test_import_pauses_after_toc()`: After background task → pipeline_status = "toc_extracted", chapters in DB
    - `test_import_with_materials_includes_relevance()`: Course has materials → response includes relevance scores
    - `test_import_without_materials_skips_relevance()`: Empty course → no relevance, just TOC + chapters
    - `test_status_endpoint_returns_pipeline_state()`: GET /textbooks/{id}/status → returns pipeline_status, chapters with extraction_status
    - `test_status_includes_relevance_when_available()`: GET /textbooks/{id}/status includes relevance_results if computed
  - **GREEN**: Modify `backend/app/routers/textbooks.py`:
    - Rewrite `POST /import` endpoint:
      - Save file, create textbook record (status: "uploaded")
      - Start background task that calls `PipelineOrchestrator.run_toc_phase()`
      - TOC phase: extract TOC, split chapters, create sections, optionally run relevance matching
      - After TOC phase: pipeline pauses at "toc_extracted" (does NOT start MinerU)
    - New `GET /textbooks/{id}/status` endpoint:
      - Return pipeline_status, list of ChapterWithStatus (id, title, extraction_status, relevance_score, matched_topics)
      - Replace `_job_status` dict lookups with DB queries
    - Keep `_job_status` dict for backward compatibility during transition (poll still works), but primary state is DB
    - Handle single-chapter books: if only 1 chapter, auto-select it (skip verification)
  - **REFACTOR**: Remove deprecated `process_pdf_background()` code paths after new pipeline proven

  **Must NOT do**:
  - Do NOT remove the existing import endpoint signature — keep same POST /import URL and form fields
  - Do NOT change the file upload mechanism (still FormData with course_id)
  - Do NOT auto-start MinerU extraction — pipeline MUST pause for verification

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Rewriting core pipeline with state machine integration, backward compatibility, error handling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 10, 11, 12)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 15, 16 (UI progress + integration tests)
  - **Blocked By**: Tasks 4, 7 (orchestrator + content extractor)

  **References**:

  **Pattern References**:
  - `backend/app/routers/textbooks.py:17-79` — Current import endpoint + `process_pdf_background()`. This is THE code being rewritten. Study the entire function.
  - `backend/app/routers/textbooks.py:15` — `_job_status` dict. Must maintain compatibility while transitioning to DB state.
  - `backend/app/routers/textbooks.py:81-90` — Current status endpoint. Must be enhanced to return pipeline state.

  **API/Type References**:
  - `backend/app/services/pipeline_orchestrator.py` — (from Task 4) Orchestrator to call for pipeline phases
  - `backend/app/models/pipeline_models.py` — ChapterWithStatus, PipelineStatus
  - `frontend/src/api/textbooks.ts` — Current frontend API calls — must maintain URL compatibility

  **Test References**:
  - `backend/tests/test_courses.py` — Existing router test pattern using `httpx.AsyncClient` with `app`

  **WHY Each Reference Matters**:
  - `textbooks.py:17-79`: The function being replaced — must understand all callers and side effects
  - `textbooks.py:15`: `_job_status` used by frontend polling — breaking this breaks the UI until Task 15
  - `test_courses.py`: Router testing pattern to follow

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_import_pipeline.py -v` → ALL PASS (6 tests)
  - [ ] POST /import returns immediately, pipeline runs in background
  - [ ] Pipeline pauses at toc_extracted (MinerU NOT called)
  - [ ] GET /textbooks/{id}/status returns chapters with extraction_status

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Import pauses after TOC extraction
    Tool: Bash (curl)
    Preconditions: Backend running, test PDF available, test course exists
    Steps:
      1. curl -s -X POST http://127.0.0.1:8000/api/textbooks/import -F "file=@test.pdf" -F "course_id=test-course"
      2. Note textbook_id from response
      3. Wait 10s for background task
      4. curl -s http://127.0.0.1:8000/api/textbooks/{id}/status | jq '.pipeline_status'
      5. Assert: pipeline_status == "toc_extracted"
      6. Assert: chapters array is non-empty
      7. Assert: NO extracted_content in DB for this textbook (MinerU not called)
    Expected Result: Pipeline paused at TOC phase, chapters listed, no extraction started
    Failure Indicators: pipeline_status is "fully_extracted" (old behavior), or chapters missing
    Evidence: .sisyphus/evidence/task-9-import-pause.txt

  Scenario: Single-chapter book skips verification
    Tool: Bash (curl + pytest)
    Preconditions: PDF with no real TOC (single chapter)
    Steps:
      1. Import single-chapter PDF
      2. Check status: should auto-select the single chapter
      3. Assert: extraction_status of single chapter != "pending"
    Expected Result: Single chapter auto-selected, verification step skipped
    Failure Indicators: Still stuck at awaiting_verification with 1 chapter
    Evidence: .sisyphus/evidence/task-9-single-chapter.txt
  ```

  **Evidence to Capture:**
  - [ ] task-9-import-pause.txt
  - [ ] task-9-single-chapter.txt

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(backend): rewrite textbook import with multi-phase pipeline`
  - Files: `backend/app/routers/textbooks.py`, `backend/tests/test_import_pipeline.py`
  - Pre-commit: `pytest backend/tests/test_import_pipeline.py -v`

- [ ] 10. Chapter Verification + Extraction API Endpoints

  **What to do**:
  - **RED**: Write `backend/tests/test_verification_api.py` with tests:
    - `test_verify_chapters_starts_extraction()`: POST /textbooks/{id}/verify-chapters with selected IDs → 200, extraction starts
    - `test_verify_sets_deferred()`: Unselected chapters get extraction_status = "deferred"
    - `test_verify_requires_toc_extracted_state()`: POST verify on "uploaded" textbook → 409 Conflict
    - `test_deferred_extraction_endpoint()`: POST /textbooks/{id}/extract-deferred with chapter IDs → 200, extraction starts
    - `test_deferred_requires_partially_extracted()`: POST extract-deferred on wrong state → 409
    - `test_extraction_progress_endpoint()`: GET /textbooks/{id}/extraction-progress → returns per-chapter status
  - **GREEN**: Add endpoints to `backend/app/routers/textbooks.py`:
    - `POST /textbooks/{id}/verify-chapters` — body: `{selected_chapter_ids: ["id1", "id2"]}` → calls orchestrator.submit_verification() + orchestrator.run_extraction_phase()
    - `POST /textbooks/{id}/extract-deferred` — body: `{chapter_ids: ["id3", "id4"]}` → calls orchestrator.run_deferred_extraction()
    - `GET /textbooks/{id}/extraction-progress` → returns {pipeline_status, chapters: [{id, title, extraction_status, ...}]}
    - All endpoints validate pipeline state before proceeding (409 if wrong state)
  - **REFACTOR**: Ensure consistent error responses across all endpoints

  **Must NOT do**:
  - Do NOT implement extraction logic — delegate to orchestrator
  - Do NOT auto-start description generation yet — orchestrator handles phase sequencing

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: REST endpoint design with state validation — moderate complexity
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9, 11, 12)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 13, 16 (frontend client + integration tests)
  - **Blocked By**: Tasks 4, 7 (orchestrator + extractor)

  **References**:

  **Pattern References**:
  - `backend/app/routers/courses.py:1-144` — Existing CRUD router pattern. Shows FastAPI endpoint structure, error responses (HTTPException), request body parsing.
  - `backend/app/routers/textbooks.py:81-90` — Existing status endpoint pattern.

  **API/Type References**:
  - `backend/app/models/pipeline_models.py` — ChapterVerificationRequest, ChapterWithStatus, PipelineStatus
  - `backend/app/services/pipeline_orchestrator.py` — Methods to call: submit_verification(), run_extraction_phase(), run_deferred_extraction()

  **WHY Each Reference Matters**:
  - `courses.py`: THE pattern for API endpoints in this project — error codes, response format, dependency injection
  - `pipeline_orchestrator.py`: The orchestrator methods this endpoint delegates to

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_verification_api.py -v` → ALL PASS (6 tests)
  - [ ] State validation rejects wrong-state requests with 409
  - [ ] Deferred extraction endpoint works independently of initial verification

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Chapter verification triggers selective extraction
    Tool: Bash (curl)
    Preconditions: Textbook in toc_extracted state with 5 chapters
    Steps:
      1. curl -s -X POST http://127.0.0.1:8000/api/textbooks/{id}/verify-chapters -H "Content-Type: application/json" -d '{"selected_chapter_ids": ["ch1", "ch3"]}'
      2. Assert: HTTP 200
      3. Assert: response contains {"status": "extracting", "selected_count": 2}
      4. curl -s http://127.0.0.1:8000/api/textbooks/{id}/extraction-progress
      5. Assert: ch1 and ch3 have extraction_status != "deferred"
      6. Assert: ch2, ch4, ch5 have extraction_status == "deferred"
    Expected Result: Only selected chapters being extracted, others deferred
    Failure Indicators: All chapters extracted, or wrong status codes
    Evidence: .sisyphus/evidence/task-10-verify-extract.txt

  Scenario: Wrong-state request returns 409
    Tool: Bash (curl)
    Preconditions: Textbook in "uploaded" state (not yet toc_extracted)
    Steps:
      1. curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8000/api/textbooks/{id}/verify-chapters -H "Content-Type: application/json" -d '{"selected_chapter_ids": ["ch1"]}'
      2. Assert: HTTP 409
    Expected Result: 409 Conflict with descriptive error message
    Failure Indicators: 200 or 500
    Evidence: .sisyphus/evidence/task-10-wrong-state.txt
  ```

  **Evidence to Capture:**
  - [ ] task-10-verify-extract.txt
  - [ ] task-10-wrong-state.txt

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(backend): add chapter verification and deferred extraction endpoints`
  - Files: `backend/app/routers/textbooks.py`, `backend/tests/test_verification_api.py`
  - Pre-commit: `pytest backend/tests/test_verification_api.py -v`

- [ ] 11. Material Upload API — Summarization + Retroactive Matching

  **What to do**:
  - **RED**: Write `backend/tests/test_material_upload_pipeline.py` with tests:
    - `test_upload_triggers_summarization()`: POST upload → material saved + summarizer called
    - `test_upload_with_textbooks_triggers_matching()`: Course has textbooks → retroactive matching runs
    - `test_upload_without_textbooks_no_matching()`: Empty course → summarization only, no matching
    - `test_summary_returned_in_response()`: Upload response includes summary preview
  - **GREEN**: Modify `backend/app/routers/university_materials.py`:
    - After saving uploaded file (existing logic), call `MaterialSummarizer.summarize()` in background task
    - After summarization, call `RetroactiveMatcher.on_material_summarized()` if textbooks exist
    - Include summary status in upload response
  - **REFACTOR**: Ensure background task doesn't block upload response

  **Must NOT do**:
  - Do NOT modify the upload file-handling logic (keep existing save mechanism)
  - Do NOT make summarization synchronous (must be background task)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integrating existing services into upload flow with background task coordination
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9, 10, 12)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 13, 16 (frontend client + integration tests)
  - **Blocked By**: Tasks 5, 8 (summarizer + retroactive matcher)

  **References**:

  **Pattern References**:
  - `backend/app/routers/university_materials.py:1-78` — Current upload endpoint. This is THE code being modified. Study the existing save logic.
  - `backend/app/routers/textbooks.py:44-79` — Background task pattern using `BackgroundTasks`.

  **API/Type References**:
  - `backend/app/services/material_summarizer.py` — (from Task 5) Summarizer to call
  - `backend/app/services/retroactive_matcher.py` — (from Task 8) Retroactive matcher to call

  **WHY Each Reference Matters**:
  - `university_materials.py`: The existing upload flow that must be EXTENDED (not replaced)
  - `textbooks.py:44-79`: Background task pattern to follow for post-upload processing

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_material_upload_pipeline.py -v` → ALL PASS (4 tests)
  - [ ] Upload returns immediately (summarization is background)
  - [ ] Retroactive matching only fires when textbooks exist

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Material upload triggers summarization
    Tool: Bash (curl)
    Preconditions: Backend running, test course exists
    Steps:
      1. curl -s -X POST http://127.0.0.1:8000/api/university-materials/ -F "file=@slides.pdf" -F "course_id=test-course"
      2. Assert: HTTP 200/201, response contains material_id
      3. Wait 15s for background summarization
      4. curl -s http://127.0.0.1:8000/api/university-materials/{id} | jq '.summary'
      5. Assert: summary is non-null with topics list
    Expected Result: Material uploaded and summarized in background
    Failure Indicators: Summary null after 15s, or upload fails
    Evidence: .sisyphus/evidence/task-11-upload-summary.txt

  Scenario: Upload to course with textbook triggers retroactive matching
    Tool: Bash (pytest)
    Preconditions: Course with textbook in toc_extracted state
    Steps:
      1. Run: pytest backend/tests/test_material_upload_pipeline.py::test_upload_with_textbooks_triggers_matching -v
      2. Assert: PASSES, matching results returned for textbook
    Expected Result: Relevance scores computed for existing textbook chapters
    Failure Indicators: No matching triggered, or error during matching
    Evidence: .sisyphus/evidence/task-11-retroactive.txt
  ```

  **Evidence to Capture:**
  - [ ] task-11-upload-summary.txt
  - [ ] task-11-retroactive.txt

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(backend): integrate material summarization and retroactive matching into upload`
  - Files: `backend/app/routers/university_materials.py`, `backend/tests/test_material_upload_pipeline.py`
  - Pre-commit: `pytest backend/tests/test_material_upload_pipeline.py -v`

- [x] 12. Extract CoursePreviewView Component from BookshelfPage

  **What to do**:
  - **RED**: Write `frontend/src/__tests__/CoursePreviewView.test.tsx` with tests:
    - `test_renders_textbook_list()`: Shows textbooks for selected course
    - `test_renders_materials_list()`: Shows university materials
    - `test_renders_tbd_panel()`: Third panel renders placeholder
    - `test_back_button_calls_handler()`: Back/Escape triggers onBack callback
    - `test_begin_study_navigates()`: Begin Study button calls navigation handler
  - **GREEN**: Extract `frontend/src/components/CoursePreviewView.tsx`:
    - Move Course Preview rendering logic from `BookshelfPage.tsx:343-483` into standalone component
    - Props: `course`, `textbooks`, `materials`, `onBack`, `onBeginStudy`, `onUpload`, `onDelete`
    - Keep all existing styling (bookshelf.css classes)
    - Update `BookshelfPage.tsx` to import and use `CoursePreviewView`
    - Verify BookshelfPage.test.tsx still passes (existing 30 tests)
  - **REFACTOR**: BookshelfPage should be significantly shorter after extraction

  **Must NOT do**:
  - Do NOT change any visual behavior — pure extraction refactor
  - Do NOT add chapter verification UI yet (Task 14)
  - Do NOT modify CSS — reuse existing classes
  - Do NOT break existing BookshelfPage tests

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure refactor — moving code between files with no new features
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9, 10, 11 — can even start in Wave 2)
  - **Parallel Group**: Wave 3 (but no backend dependencies)
  - **Blocks**: Tasks 14, 15 (chapter verification + progress UI build on this component)
  - **Blocked By**: None — can start immediately (frontend only)

  **References**:

  **Pattern References**:
  - `frontend/src/pages/BookshelfPage.tsx:343-483` — The exact code to extract. Lines 343-483 contain Course Preview rendering.
  - `frontend/src/pages/BookshelfPage.tsx:1-50` — State variables and imports. Identify which state vars belong to CoursePreview vs BookshelfPage.

  **Test References**:
  - `frontend/src/__tests__/BookshelfPage.test.tsx` — 30 existing tests. ALL must still pass after extraction. Follow this testing pattern for new component tests.

  **WHY Each Reference Matters**:
  - `BookshelfPage.tsx:343-483`: The exact lines being moved — must extract correctly without changing behavior
  - `BookshelfPage.test.tsx`: Regression safety net — existing tests must not break

  **Acceptance Criteria**:
  - [ ] `bun test frontend/src/__tests__/CoursePreviewView.test.tsx --run` → ALL PASS (5 tests)
  - [ ] `bun test frontend/src/__tests__/BookshelfPage.test.tsx --run` → ALL PASS (30 existing tests still pass)
  - [ ] `npx tsc --noEmit` → 0 errors
  - [ ] BookshelfPage.tsx is measurably shorter (< 500 lines)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Existing BookshelfPage tests still pass (regression)
    Tool: Bash (bun test)
    Preconditions: None
    Steps:
      1. Run: bun test frontend/src/__tests__/BookshelfPage.test.tsx --run
      2. Assert: 30/30 tests pass
    Expected Result: No regressions from extraction
    Failure Indicators: Any test fails
    Evidence: .sisyphus/evidence/task-12-regression.txt

  Scenario: New CoursePreviewView component tests pass
    Tool: Bash (bun test)
    Preconditions: Component extracted
    Steps:
      1. Run: bun test frontend/src/__tests__/CoursePreviewView.test.tsx --run
      2. Assert: 5/5 tests pass
    Expected Result: Extracted component works identically
    Failure Indicators: Any test fails
    Evidence: .sisyphus/evidence/task-12-preview-tests.txt
  ```

  **Evidence to Capture:**
  - [ ] task-12-regression.txt
  - [ ] task-12-preview-tests.txt

  **Commit**: YES (groups with Wave 3)
  - Message: `refactor(frontend): extract CoursePreviewView component from BookshelfPage`
  - Files: `frontend/src/components/CoursePreviewView.tsx`, `frontend/src/pages/BookshelfPage.tsx`, `frontend/src/__tests__/CoursePreviewView.test.tsx`
  - Pre-commit: `bun test frontend/src/__tests__/ --run`

- [ ] 13. Frontend API Client Updates

  **What to do**:
  - **RED**: Write test assertions in `frontend/src/__tests__/pipelineApi.test.ts`:
    - `test_getTextbookStatus_calls_correct_url()`: Fetches /textbooks/{id}/status
    - `test_verifyChapters_sends_selected_ids()`: POSTs selected chapter IDs to verify endpoint
    - `test_extractDeferred_sends_chapter_ids()`: POSTs chapter IDs to extract-deferred endpoint
    - `test_getExtractionProgress_returns_chapters()`: Fetches extraction progress
  - **GREEN**: Create `frontend/src/api/pipeline.ts`:
    - `getTextbookStatus(textbookId)` → {pipeline_status, chapters: ChapterWithStatus[]}
    - `verifyChapters(textbookId, selectedChapterIds)` → {status, selected_count}
    - `extractDeferred(textbookId, chapterIds)` → {status}
    - `getExtractionProgress(textbookId)` → {pipeline_status, chapters: ChapterWithStatus[]}
  - Follow existing API client pattern from `courses.ts` and `textbooks.ts`
  - **REFACTOR**: Ensure consistent error handling with existing API clients

  **Must NOT do**:
  - Do NOT modify existing API client files
  - Do NOT add UI logic — just API functions

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward API client functions following established patterns
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO — needs Tasks 10, 11 endpoints to exist first
  - **Parallel Group**: Wave 3 (late)
  - **Blocks**: Tasks 14, 15 (UI components call these functions)
  - **Blocked By**: Tasks 10, 11 (needs API endpoints defined)

  **References**:

  **Pattern References**:
  - `frontend/src/api/courses.ts` — Existing API client pattern. Follow EXACTLY: const BASE_URL, async functions, fetch with error handling.
  - `frontend/src/api/textbooks.ts` — Another API client pattern. Shows how textbook endpoints are called.
  - `frontend/src/api/universityMaterials.ts` — Upload API pattern.

  **API/Type References**:
  - `frontend/src/types/pipeline.ts` — (from Task 3) TypeScript types to use

  **WHY Each Reference Matters**:
  - `courses.ts`: THE template for new API functions — copy style exactly
  - `types/pipeline.ts`: Type definitions for request/response shapes

  **Acceptance Criteria**:
  - [ ] `bun test frontend/src/__tests__/pipelineApi.test.ts --run` → ALL PASS (4 tests)
  - [ ] `npx tsc --noEmit` → 0 errors
  - [ ] All functions follow existing API client patterns

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: API client functions compile and test correctly
    Tool: Bash (bun test + tsc)
    Preconditions: None
    Steps:
      1. Run: npx tsc --noEmit
      2. Assert: 0 errors
      3. Run: bun test frontend/src/__tests__/pipelineApi.test.ts --run
      4. Assert: 4/4 tests pass
    Expected Result: All API functions correctly typed and mocked tests pass
    Failure Indicators: Type errors or test failures
    Evidence: .sisyphus/evidence/task-13-api-tests.txt

  Scenario: API URLs match backend endpoints
    Tool: Bash (grep)
    Preconditions: Both backend router and frontend API client exist
    Steps:
      1. Grep frontend/src/api/pipeline.ts for URL patterns
      2. Grep backend/app/routers/textbooks.py for endpoint paths
      3. Assert: URLs match (verify-chapters, extract-deferred, status)
    Expected Result: Frontend URLs correspond exactly to backend endpoints
    Failure Indicators: URL mismatch between frontend and backend
    Evidence: .sisyphus/evidence/task-13-url-match.txt
  ```

  **Evidence to Capture:**
  - [ ] task-13-api-tests.txt
  - [ ] task-13-url-match.txt

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(frontend): add pipeline API client functions`
  - Files: `frontend/src/api/pipeline.ts`, `frontend/src/__tests__/pipelineApi.test.ts`
  - Pre-commit: `bun test frontend/src/__tests__/pipelineApi.test.ts --run && npx tsc --noEmit`

### Wave 4 — UI + Integration

- [ ] 14. Chapter Verification UI Component

  **What to do**:
  - **RED**: Write `frontend/src/__tests__/ChapterVerification.test.tsx` with tests:
    - `test_renders_chapter_list()`: Shows all chapters from API response
    - `test_chapters_toggleable()`: Click on chapter toggles selected state
    - `test_relevant_chapters_pre_selected()`: Chapters with relevance_score > 0.5 pre-checked
    - `test_relevance_badge_shown()`: Chapters with relevance data show badge ("High" / "Medium" / "Low")
    - `test_confirm_sends_selected_ids()`: Confirm button calls verifyChapters API with selected IDs
    - `test_no_chapters_shows_empty_state()`: Empty chapter list shows appropriate message
    - `test_escape_goes_back()`: Pressing Escape returns to previous view
    - `test_all_chapters_must_have_selection()`: At least one chapter must be selected to confirm
  - **GREEN**: Implement `frontend/src/components/ChapterVerification.tsx`:
    - Props: `chapters: ChapterWithStatus[]`, `onConfirm: (selectedIds: string[]) => void`, `onBack: () => void`
    - Render chapter list with: title, page range (pages X–Y), toggle switch, relevance badge
    - Pre-select chapters with relevance_score > 0.5 (if relevance data available)
    - Relevance badge: score > 0.7 = "High" (green), 0.4-0.7 = "Medium" (yellow), < 0.4 = "Low" (gray)
    - "Confirm Selection" PixelButton at bottom — disabled if no chapters selected
    - Pixel art styling: use `PixelButton`, `PixelPanel`, `var(--font-pixel)`, CSS variables from theme.css
  - Integrate into `CoursePreviewView.tsx`:
    - When `pipeline_status === "toc_extracted"`, show ChapterVerification instead of normal textbook list
    - On confirm → call `verifyChapters()` API → transition to extraction view
  - **REFACTOR**: Ensure component is self-contained (no BookshelfPage state leakage)

  **Must NOT do**:
  - Do NOT add chapter previews/descriptions in the verification list (title + page range + badge ONLY)
  - Do NOT add drag-and-drop or reordering
  - Do NOT add inline content preview
  - Do NOT modify DeskPage or any conversation features
  - Do NOT use any state management beyond useState

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI component with pixel art styling, state management, conditional rendering
  - **Skills**: [`playwright`]
    - `playwright`: For visual verification of chapter list rendering + toggle interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 15)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 16 (integration tests)
  - **Blocked By**: Tasks 12 (CoursePreviewView extracted), 13 (API client)

  **References**:

  **Pattern References**:
  - `frontend/src/pages/BookshelfPage.tsx:252-300` — Course list rendering pattern with map + click handlers. Follow this for chapter list rendering.
  - `frontend/src/pages/BookshelfPage.tsx:400-440` — Delete dialog pattern showing PixelButton + PixelDialog usage.
  - `frontend/src/components/CoursePreviewView.tsx` — (from Task 12) The parent component that will conditionally render ChapterVerification.

  **API/Type References**:
  - `frontend/src/types/pipeline.ts` — ChapterWithStatus type
  - `frontend/src/api/pipeline.ts` — (from Task 13) verifyChapters() function
  - `frontend/src/styles/theme.css` — CSS variables: `--font-pixel`, `--color-primary`, `--color-success`, `--color-warning`
  - `frontend/src/styles/bookshelf.css` — Existing styles to follow/extend for chapter list

  **Test References**:
  - `frontend/src/__tests__/BookshelfPage.test.tsx` — Testing pattern: vi.mock, screen.findByText, userEvent, waitFor

  **WHY Each Reference Matters**:
  - `BookshelfPage.tsx:252-300`: List rendering pattern with hover/click — chapter list should feel identical
  - `theme.css`: Source of truth for all CSS variables — must use these, not hardcoded colors
  - `BookshelfPage.test.tsx`: Testing patterns to follow exactly for new component tests

  **Acceptance Criteria**:
  - [ ] `bun test frontend/src/__tests__/ChapterVerification.test.tsx --run` → ALL PASS (8 tests)
  - [ ] `npx tsc --noEmit` → 0 errors
  - [ ] Chapters render with title, page range, toggle, relevance badge
  - [ ] Confirm button sends correct chapter IDs to API

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Chapter verification list renders with correct data
    Tool: Playwright (playwright skill)
    Preconditions: Backend running with textbook in toc_extracted state, chapters have relevance scores
    Steps:
      1. Navigate to http://localhost:1420
      2. Click on the course containing the textbook
      3. Wait for chapter verification list to appear (pipeline_status === toc_extracted)
      4. Assert: chapters listed with titles matching API response
      5. Assert: relevance badges visible ("High", "Medium", or "Low")
      6. Assert: high-relevance chapters pre-selected (toggle on)
      7. Screenshot the verification panel
    Expected Result: Chapter list with toggles and relevance badges, pre-selections applied
    Failure Indicators: No chapters shown, missing badges, wrong pre-selections
    Evidence: .sisyphus/evidence/task-14-verification-ui.png

  Scenario: Toggle and confirm sends correct IDs
    Tool: Playwright (playwright skill)
    Preconditions: Chapter verification list visible
    Steps:
      1. Uncheck a pre-selected chapter (click its toggle)
      2. Check a non-selected chapter
      3. Click "Confirm Selection" button
      4. Assert: Network request sent to /verify-chapters with updated chapter ID list
      5. Assert: UI transitions to extraction progress view
    Expected Result: Correct chapter IDs sent, UI transitions on success
    Failure Indicators: Wrong IDs sent, no transition, error displayed
    Evidence: .sisyphus/evidence/task-14-toggle-confirm.png
  ```

  **Evidence to Capture:**
  - [ ] task-14-verification-ui.png — screenshot of chapter list
  - [ ] task-14-toggle-confirm.png — screenshot after confirmation

  **Commit**: YES (groups with Wave 4)
  - Message: `feat(frontend): add chapter verification UI with relevance badges`
  - Files: `frontend/src/components/ChapterVerification.tsx`, `frontend/src/components/CoursePreviewView.tsx`, `frontend/src/__tests__/ChapterVerification.test.tsx`, `frontend/src/styles/bookshelf.css`
  - Pre-commit: `bun test frontend/src/__tests__/ --run && npx tsc --noEmit`

- [ ] 15. Pipeline Progress + Deferred Extraction UI

  **What to do**:
  - **RED**: Write `frontend/src/__tests__/PipelineProgress.test.tsx` with tests:
    - `test_shows_extraction_progress()`: During extraction → shows per-chapter status (extracting/extracted/error)
    - `test_shows_completed_state()`: All selected chapters extracted → shows success message
    - `test_shows_deferred_chapters()`: Lists chapters with "deferred" status separately
    - `test_extract_remaining_button()`: "Extract remaining" button visible when deferred chapters exist
    - `test_extract_remaining_calls_api()`: Button click → calls extractDeferred API with deferred chapter IDs
    - `test_error_chapter_shown()`: Chapter with error status shows error indicator
    - `test_polls_for_progress()`: Component polls extraction progress every 2s during extraction
  - **GREEN**: Implement `frontend/src/components/PipelineProgress.tsx`:
    - Props: `textbookId: string`, `initialStatus: PipelineStatus`, `chapters: ChapterWithStatus[]`
    - During extraction: poll `getExtractionProgress()` every 2s (matching existing polling pattern)
    - Render per-chapter status: extracting (spinner), extracted (checkmark), error (red X), deferred (gray)
    - After extraction complete: show summary + "Extract remaining chapters" button if deferred chapters exist
    - "Extract remaining" button → calls `extractDeferred()` with deferred chapter IDs → re-enters progress view
    - Pixel art styling consistent with existing progress indicator from Task 13 home screen
  - Integrate into `CoursePreviewView.tsx`:
    - When `pipeline_status === "extracting" || "partially_extracted"`, show PipelineProgress
    - When `pipeline_status === "fully_extracted"`, show normal textbook view with extraction status icons
  - **REFACTOR**: Reuse polling pattern from BookshelfPage upload progress

  **Must NOT do**:
  - Do NOT add WebSocket/SSE — keep polling pattern
  - Do NOT show content previews during extraction
  - Do NOT auto-trigger deferred extraction

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Progress UI with polling, conditional rendering, pixel art styling
  - **Skills**: [`playwright`]
    - `playwright`: For visual verification of progress states

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 14)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 16 (integration tests)
  - **Blocked By**: Tasks 12 (CoursePreviewView), 13 (API client), 9 (pipeline produces these states)

  **References**:

  **Pattern References**:
  - `frontend/src/pages/BookshelfPage.tsx:86-109` — Existing upload polling pattern: `setInterval` every 2s, check status, clear on completion. REUSE this pattern.
  - `frontend/src/pages/BookshelfPage.tsx:470-500` — Existing progress indicator rendering (gradient fill, step text). Match this visual style.

  **API/Type References**:
  - `frontend/src/api/pipeline.ts` — (from Task 13) getExtractionProgress(), extractDeferred()
  - `frontend/src/types/pipeline.ts` — PipelineStatus, ExtractionStatus, ChapterWithStatus

  **WHY Each Reference Matters**:
  - `BookshelfPage.tsx:86-109`: THE polling pattern to reuse — don't reinvent
  - `BookshelfPage.tsx:470-500`: Visual progress style to match for consistency

  **Acceptance Criteria**:
  - [ ] `bun test frontend/src/__tests__/PipelineProgress.test.tsx --run` → ALL PASS (7 tests)
  - [ ] `npx tsc --noEmit` → 0 errors
  - [ ] Polling updates progress in real-time
  - [ ] "Extract remaining" button works for deferred chapters

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Extraction progress shown per-chapter
    Tool: Playwright (playwright skill)
    Preconditions: Textbook with chapters in "extracting" state
    Steps:
      1. Navigate to course preview for the textbook
      2. Assert: progress view visible with per-chapter status indicators
      3. Wait for extraction to complete (poll updates)
      4. Assert: completed chapters show checkmark icon
      5. Screenshot the progress view
    Expected Result: Real-time progress updates, clear per-chapter status
    Failure Indicators: No progress shown, stuck state, missing chapters
    Evidence: .sisyphus/evidence/task-15-progress-view.png

  Scenario: Deferred extraction triggered via button
    Tool: Playwright (playwright skill)
    Preconditions: Textbook in partially_extracted state with deferred chapters
    Steps:
      1. Navigate to course preview
      2. Find "Extract remaining chapters" button
      3. Click button
      4. Assert: deferred chapters transition to "extracting" state
      5. Assert: progress view re-appears for deferred chapters
    Expected Result: Deferred extraction starts, progress shown
    Failure Indicators: Button missing, click has no effect, error displayed
    Evidence: .sisyphus/evidence/task-15-deferred-extract.png
  ```

  **Evidence to Capture:**
  - [ ] task-15-progress-view.png
  - [ ] task-15-deferred-extract.png

  **Commit**: YES (groups with Wave 4)
  - Message: `feat(frontend): add pipeline progress view and deferred extraction button`
  - Files: `frontend/src/components/PipelineProgress.tsx`, `frontend/src/components/CoursePreviewView.tsx`, `frontend/src/__tests__/PipelineProgress.test.tsx`, `frontend/src/styles/bookshelf.css`
  - Pre-commit: `bun test frontend/src/__tests__/ --run && npx tsc --noEmit`

- [ ] 16. Integration Testing — Full Pipeline End-to-End

  **What to do**:
  - **RED + GREEN combined** (integration tests test the full system):
  - Write `backend/tests/test_pipeline_integration.py` with end-to-end tests:
    - `test_full_pipeline_textbook_first()`: Import textbook to empty course → TOC extracted → verify chapters → extract → descriptions generated → content stored
    - `test_full_pipeline_with_materials()`: Upload materials → import textbook → relevance matching → verify → extract
    - `test_retroactive_matching_flow()`: Import textbook → upload materials later → retroactive matching triggers
    - `test_deferred_extraction_flow()`: Import → select 2 of 5 chapters → extract → defer rest → manual extract remaining
    - `test_single_chapter_book_flow()`: Single-chapter PDF → auto-selected → extracted without verification
    - `test_concurrent_imports()`: Two textbooks importing simultaneously → no state conflicts
    - `test_error_recovery()`: MinerU fails for one chapter → others succeed → error chapter can be retried
  - These are INTEGRATION tests — they test the real pipeline with mocked external services (DeepSeek, MinerU)
  - **REFACTOR**: Extract common test fixtures for reuse

  **Must NOT do**:
  - Do NOT test against real DeepSeek API (mock it)
  - Do NOT test against real MinerU (mock it — use spike results for realistic mock data)
  - Do NOT test frontend-backend integration (that's F3's job)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex integration test scenarios with multiple services, state transitions, error handling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO — depends on ALL previous tasks
  - **Parallel Group**: Wave 4 (serial — after 14, 15)
  - **Blocks**: F1-F4 (final review wave)
  - **Blocked By**: Tasks 9, 10, 11, 14, 15 (needs full pipeline + UI)

  **References**:

  **Pattern References**:
  - ALL backend test files — Fixture patterns, mock patterns, async test patterns
  - `backend/app/services/pipeline_orchestrator.py` — Full pipeline flow to test

  **API/Type References**:
  - All backend router endpoints — Testing the full REST API surface

  **WHY Each Reference Matters**:
  - Integration tests exercise the REAL interaction between all components — must understand the full pipeline flow

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_pipeline_integration.py -v` → ALL PASS (7 tests)
  - [ ] All pipeline states correctly transitioned
  - [ ] Concurrent imports don't conflict
  - [ ] Error recovery works as designed

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full textbook-first pipeline
    Tool: Bash (pytest)
    Preconditions: Mocked DeepSeek + MinerU
    Steps:
      1. Run: pytest backend/tests/test_pipeline_integration.py::test_full_pipeline_textbook_first -v
      2. Assert: PASSES
      3. Verify: textbook goes through uploaded → toc_extracted → extracting → partially_extracted
      4. Verify: extracted_content table has entries for selected chapters
      5. Verify: deferred chapters have extraction_status = "deferred"
    Expected Result: Full pipeline flow completes correctly
    Failure Indicators: Any state transition fails, or content not stored
    Evidence: .sisyphus/evidence/task-16-integration-full.txt

  Scenario: Concurrent imports don't conflict
    Tool: Bash (pytest)
    Preconditions: Two test PDFs, two courses
    Steps:
      1. Run: pytest backend/tests/test_pipeline_integration.py::test_concurrent_imports -v
      2. Assert: PASSES, both imports complete independently
    Expected Result: No state conflicts, both textbooks processed correctly
    Failure Indicators: State mixing between imports, DB errors, deadlocks
    Evidence: .sisyphus/evidence/task-16-concurrent.txt
  ```

  **Evidence to Capture:**
  - [ ] task-16-integration-full.txt
  - [ ] task-16-concurrent.txt

  **Commit**: YES (groups with Wave 4)
  - Message: `test(backend): add end-to-end pipeline integration tests`
  - Files: `backend/tests/test_pipeline_integration.py`
  - Pre-commit: `pytest backend/tests/test_pipeline_integration.py -v`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `npx tsc --noEmit` + `bun test` + `pytest`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp). Verify all new services have proper error handling.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill)
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (full pipeline from import to extraction). Test edge cases: empty course, single-chapter book, material upload before textbook. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `feat(backend): add content pipeline schema migrations and MinerU spike` — storage.py, models, spike test
- **Wave 2**: `feat(backend): add pipeline orchestrator, material summarizer, relevance matcher, selective extractor` — new service files + tests
- **Wave 3**: `feat(backend): rewrite textbook import API with multi-phase pipeline` — router changes + API tests; `refactor(frontend): extract CoursePreviewView component` — component extraction
- **Wave 4**: `feat(frontend): add chapter verification and pipeline progress UI` — new components + tests; `test: add end-to-end pipeline integration tests`

---

## Success Criteria

### Verification Commands
```bash
# Backend tests
pytest backend/tests/ -v  # Expected: ALL PASS

# Frontend tests  
bun test frontend/src/__tests__/ --run  # Expected: ALL PASS

# TypeScript
npx tsc --noEmit  # Expected: 0 errors

# Smoke test: Import textbook (should pause at TOC)
curl -s -X POST http://127.0.0.1:8000/api/textbooks/import \
  -F "file=@test.pdf" -F "course_id=test-course" \
  | jq '.status'  # Expected: "toc_extracted"

# Smoke test: Verify chapters
curl -s -X POST http://127.0.0.1:8000/api/textbooks/{id}/verify-chapters \
  -H "Content-Type: application/json" \
  -d '{"selected_chapter_ids": ["ch1", "ch3"]}' \
  | jq '.status'  # Expected: "extracting"

# Smoke test: Upload material triggers summarization
curl -s -X POST http://127.0.0.1:8000/api/university-materials/ \
  -F "file=@slides.pdf" -F "course_id=test-course" \
  | jq '.summary'  # Expected: non-null summary object
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All pytest tests pass
- [ ] All vitest tests pass
- [ ] TypeScript clean (0 errors)
- [ ] Pipeline pauses for verification (not automatic)
- [ ] Extracted content has separate DB records per type
- [ ] Deferred extraction works via manual trigger
- [ ] Retroactive matching fires on material upload
