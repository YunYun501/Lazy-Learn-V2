# Home Screen Redesign — Course-Centric 3-Column Layout

## TL;DR

> **Quick Summary**: Redesign Lazy Learn's home screen from a simple bookshelf (BookSpine list) to a course-centric 3-column layout with a new Course data model, backend CRUD, upload dialogs, delete confirmations, CSS pixel art scenery, and a Course Preview view with sub-panels.
> 
> **Deliverables**:
> - Backend: Courses CRUD router (`/api/courses`), university_materials table + endpoints, textbooks.course_id migration
> - Frontend: Complete BookshelfPage.tsx rewrite with 3-column layout, HOME_VIEW ↔ COURSE_PREVIEW_VIEW state machine
> - Frontend: Upload dialog (Textbook vs University Material), delete confirmation dialog, course creation dialog
> - Frontend: CSS-only pixel art scenery, hover glow + click-to-lock selection, course progress indicator
> - Frontend: `courses.ts` + `universityMaterials.ts` API clients
> - Tests: Full pytest + vitest coverage for all new code, BookshelfPage.test.tsx rewrite
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: Task 1 (schema migration) → Task 3 (courses router) → Task 7 (BookshelfPage rewrite) → Task 10 (Course Preview) → F1-F4

---

## Context

### Original Request
Redesign the Lazy Learn home screen from a bookshelf layout to a course-centric design where courses are the primary organizational unit. Courses group textbooks + university materials. The layout should be a 3-column design with pixel art scenery, and users should be able to create courses, upload materials, preview course contents, and begin studying.

### Interview Summary
**Key Discussions**:
- **Courses are NEW**: A course (e.g. "Control Systems 101") groups textbooks + university materials. The `courses` table exists in SQLite but is totally unused — no router, no frontend integration.
- **3-column layout**: Book Shelf (left ~25%) | Scenery + Study Desk (middle ~40%) | Reserve Space (right ~25%)
- **Two views**: HOME_VIEW (default, course list + scenery) and COURSE_PREVIEW_VIEW (3 sub-panels: Textbooks | University Content | TBD)
- **Upload dialog**: PixelDialog asking "Textbook or University Material?" with two paths
- **Delete**: Cascade delete everything (textbooks + files + DB records), requires confirmation dialog
- **Course creation**: Dedicated "+ New Course" button opens PixelDialog for name input
- **Math Library**: Becomes a special reserved "Math Library" course, auto-created, can't be deleted
- **University material types**: All common formats (.pdf, .pptx, .docx, .txt, .md, .xlsx)
- **Navigation**: "Begin study" in Course Preview → `/desk/:textbookId` (user selects a textbook)
- **Scenery**: CSS-only pixel art, ONE static scene for v1 (dynamic deferred to v2)
- **Settings**: Button in top-right corner, navigates to existing `/settings`

**Research Findings**:
- `courses.id` is TEXT (UUID), not INTEGER — `course_id` FK must be TEXT
- `textbooks.course` stores NAME not ID — migration needed to add `course_id` column
- No migration framework — use `ALTER TABLE` in `initialize()` with try/except
- `PRAGMA foreign_keys` never enabled — cascade delete must be application-level
- MetadataStore has `create_course()` and `list_courses()` but missing get/update/delete
- PixelDialog exists at `frontend/src/components/pixel/PixelDialog.tsx` (isOpen, onClose, title, children)
- Existing BookshelfPage.test.tsx will need complete rewrite
- `conversations.course_id` already exists in schema

### Metis Review
**Identified Gaps** (addressed):
- Math Library fate → Special reserved course
- Course creation flow → Dedicated "+ New Course" button
- University material types → All common formats
- `course_id` type → TEXT (UUID), not INTEGER
- `university_materials` table → Needs to be designed from scratch
- Cascade delete → Application-level (no FK enforcement in SQLite)
- CSS layout math (25+40+25=90%) → Use CSS grid with gap
- Long course names → CSS text-overflow: ellipsis
- Delete during active upload → Block deletion
- Empty course "Begin Study" → Disabled with tooltip

---

## Work Objectives

### Core Objective
Replace the current BookshelfPage's flat textbook list with a course-centric home screen that organizes materials by course, supports creating/deleting courses, uploading textbooks and university materials, previewing course contents, and navigating to study sessions.

### Concrete Deliverables
- `backend/app/routers/courses.py` — Full CRUD router for courses
- `backend/app/services/storage.py` — Extended MetadataStore with course + university_materials methods
- `frontend/src/pages/BookshelfPage.tsx` — Complete rewrite with 3-column layout
- `frontend/src/styles/bookshelf.css` — Complete restyle
- `frontend/src/api/courses.ts` — Courses API client
- `frontend/src/api/universityMaterials.ts` — University materials API client
- `frontend/src/__tests__/BookshelfPage.test.tsx` — Complete rewrite
- `backend/tests/test_courses.py` — Courses router tests

### Definition of Done
- [ ] `cd backend && python -m pytest tests/test_courses.py` → PASS
- [ ] `cd frontend && npx vitest run src/__tests__/BookshelfPage.test.tsx` → PASS
- [ ] 3-column layout renders at `/` with course list, scenery, and reserve space
- [ ] User can create, select, preview, upload to, and delete courses
- [ ] Upload dialog distinguishes textbook vs university material
- [ ] Delete confirmation dialog prevents accidental deletion
- [ ] CSS pixel art scenery renders without image assets
- [ ] "Begin study" navigates to `/desk/:textbookId`

### Must Have
- Course CRUD (create, read, update name, delete with cascade)
- University materials table + basic CRUD
- `textbooks.course_id` TEXT column (FK to courses.id)
- "Math Library" special reserved course (auto-created, non-deletable)
- "+ New Course" button with name input dialog
- Upload dialog with Textbook vs University Material choice
- Delete confirmation dialog (PixelDialog, not window.confirm)
- 3-column layout with CSS grid
- HOME_VIEW ↔ COURSE_PREVIEW_VIEW state machine
- Course list with search filter, hover glow, click-to-lock selection
- Course Preview with 3 sub-panels (Textbooks | University Content | TBD)
- "Begin study" button navigating to `/desk/:textbookId`
- CSS-only pixel art scenery (ONE static scene)
- Settings button top-right corner
- Upload progress shown on course bar item
- Keyboard accessibility (Tab, Enter, Escape)

### Must NOT Have (Guardrails)
- **NO** global state management (Redux, Zustand, Jotai) — useState only
- **NO** pixel art image assets — CSS-only for v1 (box-shadow technique)
- **NO** university material AI processing — store file + metadata only
- **NO** DeskPage.tsx modifications
- **NO** SettingsPage.tsx modifications
- **NO** new react-router routes — HOME_VIEW/COURSE_PREVIEW_VIEW are component-internal state at `/`
- **NO** `PRAGMA foreign_keys` enablement — cascade delete is application-level
- **NO** dropping `textbooks.course` TEXT column — keep both columns during transition
- **NO** changes to `courses.id` type — stays TEXT (UUID)
- **NO** functionality in Reserve Space column — empty PixelPanel with "Coming Soon"
- **NO** more than ONE CSS scenery scene for v1
- **NO** animation beyond CSS transitions (no requestAnimationFrame, no JS animation loops)
- **NO** scenery that changes based on context in v1 (deferred to v2)
- **NO** drag-to-reorder courses
- **NO** course fields beyond `id, name, created_at` for v1

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (vitest frontend, pytest backend)
- **Automated tests**: YES (TDD)
- **Backend framework**: pytest + pytest-asyncio
- **Frontend framework**: vitest + React Testing Library
- **If TDD**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright (playwright skill) — Navigate, interact, assert DOM, screenshot
- **API/Backend**: Use Bash (curl) — Send requests, assert status + response fields
- **Database**: Use Bash (python scripts) — Query SQLite, verify schema + data integrity

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — backend schema + API clients):
├── Task 1: Schema migration + MetadataStore extensions [quick]
├── Task 2: University materials table + MetadataStore methods [quick]
├── Task 3: Courses CRUD router [unspecified-high]
├── Task 4: University materials upload router [unspecified-high]
├── Task 5: Frontend courses.ts API client [quick]
└── Task 6: Frontend universityMaterials.ts API client [quick]

Wave 2 (Core UI — after Wave 1, MAX PARALLEL):
├── Task 7: BookshelfPage.tsx rewrite — 3-column layout + HOME_VIEW [visual-engineering]
├── Task 8: Course creation dialog [quick]
├── Task 9: Upload dialog (Textbook vs University Material) [quick]
└── Task 10: Delete confirmation dialog [quick]

Wave 3 (Feature completion — after Wave 2):
├── Task 11: Course Preview view + "Begin study" navigation [visual-engineering]
├── Task 12: CSS pixel art scenery component [visual-engineering]
├── Task 13: Course bar progress indicator [quick]
└── Task 14: BookshelfPage.test.tsx rewrite [unspecified-high]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA — full flow with Playwright (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: T1 → T3 → T7 → T11 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 6 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 3, 4, 7 | 1 |
| 2 | — | 4, 6 | 1 |
| 3 | 1 | 7, 8, 9, 10, 11 | 1 |
| 4 | 1, 2 | 9 | 1 |
| 5 | — | 7, 8, 9, 10, 11 | 1 |
| 6 | — | 9, 11 | 1 |
| 7 | 1, 3, 5 | 8, 9, 10, 11, 12, 13, 14 | 2 |
| 8 | 3, 5, 7 | 14 | 2 |
| 9 | 3, 4, 5, 6, 7 | 14 | 2 |
| 10 | 3, 5, 7 | 14 | 2 |
| 11 | 3, 5, 6, 7 | 14 | 3 |
| 12 | 7 | 14 | 3 |
| 13 | 7 | 14 | 3 |
| 14 | 7, 8, 9, 10, 11, 12, 13 | — | 3 |

### Agent Dispatch Summary

- **Wave 1**: 6 — T1 → `quick`, T2 → `quick`, T3 → `unspecified-high`, T4 → `unspecified-high`, T5 → `quick`, T6 → `quick`
- **Wave 2**: 4 — T7 → `visual-engineering`, T8 → `quick`, T9 → `quick`, T10 → `quick`
- **Wave 3**: 4 — T11 → `visual-engineering`, T12 → `visual-engineering`, T13 → `quick`, T14 → `unspecified-high`
- **FINAL**: 4 — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.


- [x] 1. Schema Migration — Add course_id to textbooks + university_materials table

  **What to do**:
  - Add `ALTER TABLE textbooks ADD COLUMN course_id TEXT` in `MetadataStore.initialize()`, wrapped in `try/except` (sqlite3.OperationalError for duplicate column) for idempotency
  - Create `university_materials` table in `CREATE_TABLES_SQL`:
    ```sql
    CREATE TABLE IF NOT EXISTS university_materials (
        id TEXT PRIMARY KEY,
        course_id TEXT NOT NULL,
        title TEXT NOT NULL,
        file_type TEXT NOT NULL,
        filepath TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    ```
  - Add new MetadataStore methods:
    - `async def get_course(self, course_id: str) -> Optional[dict]`
    - `async def update_course(self, course_id: str, name: str) -> dict`
    - `async def delete_course(self, course_id: str)` — Application-level cascade: delete files on disk (shutil.rmtree textbook dirs + description dirs) → delete chapters → delete textbooks → delete university_materials → delete course record. All within a single async DB connection.
    - `async def assign_textbook_to_course(self, textbook_id: str, course_id: str)`
    - `async def get_course_textbooks(self, course_id: str) -> list[dict]`
  - Add university_materials MetadataStore methods:
    - `async def create_university_material(self, course_id, title, file_type, filepath) -> dict`
    - `async def list_university_materials(self, course_id: str) -> list[dict]`
    - `async def delete_university_material(self, material_id: str)`
  - Ensure "Math Library" course is auto-created in `initialize()` if it doesn't exist (use `INSERT OR IGNORE` since name has UNIQUE constraint)
  - When creating new textbooks via upload flow, set BOTH `course` (name) AND `course_id` (UUID) for backward compatibility
  - TDD: Test `ALTER TABLE` idempotency (running initialize twice doesn't error)
  - TDD: Test cascade delete removes all related records + files
  - TDD: Test Math Library auto-creation on initialize
  - TDD: Test university_materials CRUD operations

  **Must NOT do**:
  - Do NOT drop `textbooks.course` TEXT column — keep both columns during transition
  - Do NOT enable `PRAGMA foreign_keys` — cascade delete is application-level
  - Do NOT change `courses.id` from TEXT — stays UUID
  - Do NOT use any ORM or migration framework

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Schema changes + CRUD methods following existing patterns in storage.py
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: Not needed — backend-only task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5, 6)
  - **Blocks**: Tasks 3, 4, 7
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References** (existing code to follow):
  - `backend/app/services/storage.py:9-52` — `CREATE_TABLES_SQL` pattern for adding university_materials table
  - `backend/app/services/storage.py:54-60` — `initialize()` method where ALTER TABLE + auto-create Math Library goes
  - `backend/app/services/storage.py:62-80` — `create_textbook()` method — pattern for new CRUD methods
  - `backend/app/services/storage.py:163-175` — Existing `create_course()` and `list_courses()` methods

  **API/Type References**:
  - `backend/app/services/storage.py:11` — `courses.id TEXT PRIMARY KEY` — confirms course_id must be TEXT
  - `backend/app/services/storage.py:16-24` — textbooks table schema — where `course_id TEXT` column gets added

  **Test References**:
  - `backend/tests/test_storage.py` — Existing storage test pattern with async fixtures and temp DB

  **WHY Each Reference Matters**:
  - `storage.py:9-52` defines the canonical table creation pattern — new table must match this style exactly
  - `storage.py:163-175` shows how create_course and list_courses are implemented — new methods follow same pattern
  - `test_storage.py` shows how to create temp DB fixtures for isolated testing

  **Acceptance Criteria**:
  - [ ] Test file: `backend/tests/test_courses_storage.py`
  - [ ] `cd backend && python -m pytest tests/test_courses_storage.py -v` → PASS (8+ tests)
  - [ ] `university_materials` table created on initialize
  - [ ] `textbooks.course_id` column exists after initialize
  - [ ] Math Library course auto-created on initialize
  - [ ] Cascade delete removes textbooks + university_materials + chapters + files

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Schema migration is idempotent
    Tool: Bash (python script)
    Preconditions: Backend installed, data/lazy_learn.db exists
    Steps:
      1. Run: python -c "import asyncio; from app.services.storage import MetadataStore; s=MetadataStore(); asyncio.run(s.initialize()); asyncio.run(s.initialize()); print('OK')"
      2. Verify no errors on second initialize call
      3. Run: python -c "import asyncio, aiosqlite; asyncio.run((lambda: __import__('asyncio').get_event_loop().run_until_complete(aiosqlite.connect('data/lazy_learn.db')))())" — verify course_id column exists via PRAGMA table_info(textbooks)
    Expected Result: Both initialize calls succeed, course_id column present, university_materials table present
    Failure Indicators: OperationalError on second call, missing column
    Evidence: .sisyphus/evidence/task-1-schema-idempotent.txt

  Scenario: Cascade delete removes everything
    Tool: Bash (pytest)
    Preconditions: Test DB with course + textbooks + university_materials + chapters
    Steps:
      1. Create a course with 2 textbooks and 1 university material
      2. Call delete_course(course_id)
      3. Verify: course record gone, textbook records gone, university_material records gone, chapter records gone
    Expected Result: All related records deleted, zero orphans
    Failure Indicators: Any related records still exist after delete
    Evidence: .sisyphus/evidence/task-1-cascade-delete.txt

  Scenario: Math Library auto-created and non-deletable pattern
    Tool: Bash (pytest)
    Preconditions: Fresh DB
    Steps:
      1. Initialize MetadataStore
      2. list_courses() — verify 'Math Library' exists
      3. Attempt delete_course() on Math Library — verify it raises/blocks
    Expected Result: Math Library present after init, delete blocked
    Failure Indicators: Math Library missing, or successfully deleted
    Evidence: .sisyphus/evidence/task-1-math-library.txt
  ```

  **Evidence to Capture:**
  - [ ] Schema verification output showing all tables + columns
  - [ ] Cascade delete test output
  - [ ] Math Library auto-creation verification

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(storage): schema migration — course_id FK, university_materials table, cascade delete`
  - Files: `backend/app/services/storage.py`, `backend/tests/test_courses_storage.py`
  - Pre-commit: `cd backend && python -m pytest tests/test_courses_storage.py`

---

- [x] 2. University Materials Upload Router — File Storage + Metadata

  **What to do**:
  - Create `backend/app/routers/university_materials.py` with FastAPI router:
    - `POST /api/university-materials/upload` — Accepts file upload + `course_id` form field
      - Validates `course_id` exists (404 if not)
      - Validates file extension against allowed types: `.pdf, .pptx, .docx, .txt, .md, .xlsx`
      - Saves file to `data/university_materials/{course_id}/{uuid}_{original_filename}`
      - Creates DB record via MetadataStore
      - Returns `{id, title, file_type, filepath, course_id, created_at}`
    - `GET /api/university-materials?course_id={id}` — List materials for a course
    - `DELETE /api/university-materials/{id}` — Delete material record + file from disk
  - Register router in `backend/app/main.py` following existing pattern (L16-24)
  - File storage: No processing — just save the raw file to disk
  - TDD: Test upload with valid PDF → 200 + record created
  - TDD: Test upload with invalid extension → 400
  - TDD: Test upload with non-existent course_id → 404
  - TDD: Test delete removes file + record

  **Must NOT do**:
  - Do NOT process or parse university materials — just store the file
  - Do NOT use material_organizer.py — that's out of scope
  - Do NOT add AI processing pipelines

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Router with file handling, validation, and multiple endpoints
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5, 6)
  - **Blocks**: Tasks 4, 6
  - **Blocked By**: None (can start immediately — uses MetadataStore methods from Task 1, but can develop against the interface)

  **References**:

  **Pattern References** (existing code to follow):
  - `backend/app/routers/textbooks.py:13-19` — Router setup pattern with APIRouter prefix + get_storage() factory
  - `backend/app/routers/textbooks.py:83-95` — File upload endpoint pattern (FormData, file validation)
  - `backend/app/main.py:16-24` — Router registration pattern

  **API/Type References**:
  - `backend/app/services/storage.py` — MetadataStore methods from Task 1 (create_university_material, list_university_materials, delete_university_material)

  **WHY Each Reference Matters**:
  - `textbooks.py:13-19` defines the exact FastAPI router pattern — prefix, tags, get_storage helper. New router MUST match this.
  - `textbooks.py:83-95` shows how file uploads are handled — FormData, file extension check, save to disk. Follow same pattern but with different allowed extensions.
  - `main.py:16-24` shows how to mount the router — `app.include_router()`

  **Acceptance Criteria**:
  - [ ] Test file: `backend/tests/test_university_materials.py`
  - [ ] `cd backend && python -m pytest tests/test_university_materials.py -v` → PASS (4+ tests)
  - [ ] Router registered in main.py
  - [ ] File saved to correct path on disk
  - [ ] DB record created with correct fields

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Upload a PDF university material
    Tool: Bash (curl)
    Preconditions: Backend running, at least one course exists
    Steps:
      1. Get a course ID: curl -s http://localhost:8000/api/courses | python -c "import sys,json; print(json.load(sys.stdin)[0]['id'])"
      2. Upload: curl -s -X POST http://localhost:8000/api/university-materials/upload -F 'file=@test_file.pdf' -F 'course_id={course_id}'
      3. Verify response has id, title, file_type='pdf', course_id
      4. List: curl -s http://localhost:8000/api/university-materials?course_id={course_id} | python -c "import sys,json; data=json.load(sys.stdin); assert len(data)>=1; print('OK')"
    Expected Result: Upload returns 200 with metadata, list returns the uploaded material
    Failure Indicators: 500 error, missing fields, file not saved to disk
    Evidence: .sisyphus/evidence/task-2-upload-pdf.txt

  Scenario: Reject upload with invalid file extension
    Tool: Bash (curl)
    Preconditions: Backend running, course exists
    Steps:
      1. Create a file with .exe extension: echo 'test' > test_file.exe
      2. Upload: curl -s -w '%{http_code}' -X POST http://localhost:8000/api/university-materials/upload -F 'file=@test_file.exe' -F 'course_id={course_id}'
      3. Verify HTTP 400 response
    Expected Result: 400 error with message about unsupported file type
    Failure Indicators: 200 response (file accepted), 500 error
    Evidence: .sisyphus/evidence/task-2-reject-invalid.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(api): university materials upload router — store + metadata only`
  - Files: `backend/app/routers/university_materials.py`, `backend/tests/test_university_materials.py`, `backend/app/main.py`
  - Pre-commit: `cd backend && python -m pytest tests/test_university_materials.py`

---

- [x] 3. Courses CRUD Router — Full API Endpoints

  **What to do**:
  - Create `backend/app/routers/courses.py` with FastAPI router:
    - `POST /api/courses` — Create course with `{name}` body. Returns `{id, name, created_at}`. Rejects duplicate names with 409.
    - `GET /api/courses` — List all courses. Returns array of `{id, name, created_at, textbook_count, material_count}`.
    - `GET /api/courses/{id}` — Get single course with textbook + material counts.
    - `PUT /api/courses/{id}` — Update course name. Rejects if name taken (409). Blocks rename of Math Library.
    - `DELETE /api/courses/{id}` — Cascade delete via MetadataStore. Returns 200. Blocks deletion of Math Library (403). Blocks deletion if course has active upload jobs (409).
  - Register router in `backend/app/main.py`
  - Follow exact pattern from `textbooks.py:13-19` (APIRouter prefix, get_storage factory)
  - For textbook_count and material_count in list response: use SQL COUNT with JOIN or subquery
  - Active upload check: check `_job_status` dict in textbooks.py for any jobs where textbook.course_id == course being deleted. If any are 'processing', block the delete.
  - TDD: Test all 5 endpoints
  - TDD: Test duplicate name rejection (409)
  - TDD: Test Math Library delete blocked (403)
  - TDD: Test Math Library rename blocked (403)

  **Must NOT do**:
  - Do NOT add fields beyond `id, name, created_at` to courses table
  - Do NOT implement course reordering
  - Do NOT add pagination — simple list is fine for v1

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Full CRUD with business logic (Math Library protection, cascade delete, active upload check)
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (partially — depends on Task 1 for MetadataStore methods)
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4, 5, 6)
  - **Blocks**: Tasks 7, 8, 9, 10, 11
  - **Blocked By**: Task 1

  **References**:

  **Pattern References** (existing code to follow):
  - `backend/app/routers/textbooks.py:13-19` — Router setup with APIRouter prefix + get_storage()
  - `backend/app/routers/textbooks.py:21-36` — GET list endpoint pattern
  - `backend/app/routers/textbooks.py:38-42` — GET single item pattern
  - `backend/app/routers/textbooks.py:141-163` — DELETE endpoint pattern with file cleanup
  - `backend/app/main.py:16-24` — Router registration pattern

  **API/Type References**:
  - `backend/app/services/storage.py` — MetadataStore methods from Task 1
  - `backend/app/routers/textbooks.py:44-80` — `_job_status` dict pattern for checking active uploads

  **WHY Each Reference Matters**:
  - `textbooks.py` is the template for ALL router patterns — prefix, tags, dependency injection, error handling, response shape
  - `_job_status` dict needs to be checked cross-router to prevent deleting a course while its textbooks are being processed

  **Acceptance Criteria**:
  - [ ] Test file: `backend/tests/test_courses.py`
  - [ ] `cd backend && python -m pytest tests/test_courses.py -v` → PASS (8+ tests)
  - [ ] All 5 CRUD endpoints work
  - [ ] Duplicate name returns 409
  - [ ] Math Library delete returns 403
  - [ ] Math Library rename returns 403

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full CRUD lifecycle
    Tool: Bash (curl)
    Preconditions: Backend running
    Steps:
      1. POST /api/courses with {"name": "MECH0089"} → verify 200 + UUID
      2. GET /api/courses → verify list contains MECH0089
      3. GET /api/courses/{id} → verify name is MECH0089
      4. PUT /api/courses/{id} with {"name": "MECH0090"} → verify name updated
      5. DELETE /api/courses/{id} → verify 200
      6. GET /api/courses → verify MECH0089/MECH0090 no longer present
    Expected Result: All operations succeed in sequence
    Failure Indicators: Any non-200 response, data not persisted/deleted
    Evidence: .sisyphus/evidence/task-3-crud-lifecycle.txt

  Scenario: Math Library is protected
    Tool: Bash (curl)
    Preconditions: Backend running (Math Library auto-created)
    Steps:
      1. GET /api/courses → find Math Library course ID
      2. DELETE /api/courses/{math_library_id} → verify 403
      3. PUT /api/courses/{math_library_id} with {"name": "Renamed"} → verify 403
    Expected Result: Both delete and rename are blocked with 403
    Failure Indicators: 200 response (operation succeeded), 500 error
    Evidence: .sisyphus/evidence/task-3-math-library-protected.txt

  Scenario: Duplicate course name rejected
    Tool: Bash (curl)
    Preconditions: Backend running, "MECH0089" course exists
    Steps:
      1. POST /api/courses with {"name": "MECH0089"}
      2. Verify 409 response with error detail
    Expected Result: 409 Conflict with descriptive error message
    Failure Indicators: 200 (duplicate created), 500 error
    Evidence: .sisyphus/evidence/task-3-duplicate-rejected.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(api): courses CRUD router with Math Library protection + cascade delete`
  - Files: `backend/app/routers/courses.py`, `backend/tests/test_courses.py`, `backend/app/main.py`
  - Pre-commit: `cd backend && python -m pytest tests/test_courses.py`

---

- [x] 4. Modify Textbook Upload — Add course_id to Import Flow

  **What to do**:
  - Modify existing `POST /api/textbooks/import` in `textbooks.py` to accept optional `course_id` form field (alongside existing `course` name field)
  - When `course_id` is provided: validate course exists (404 if not), store both `course_id` AND `course` (name lookup from courses table) on the textbook record
  - Modify `importTextbook()` in `frontend/src/api/textbooks.ts` to accept optional `course_id` parameter and include it in FormData
  - Update `Textbook` interface in `textbooks.ts` to include `course_id: string | null` field
  - TDD: Test import with course_id sets both fields
  - TDD: Test import with non-existent course_id returns 404

  **Must NOT do**:
  - Do NOT remove the existing `course` (name) form field — keep backward compatibility
  - Do NOT change the MinerU processing pipeline
  - Do NOT modify how progress tracking works

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small modification to existing endpoint + API client
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5, 6)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 1 (needs course_id column)

  **References**:

  **Pattern References** (existing code to follow):
  - `backend/app/routers/textbooks.py:83-120` — Existing import endpoint — add course_id form field here
  - `frontend/src/api/textbooks.ts:37-50` — Existing `importTextbook()` function — add course_id to FormData
  - `frontend/src/api/textbooks.ts:3-10` — `Textbook` interface — add course_id field

  **WHY Each Reference Matters**:
  - The import endpoint already accepts `course` as a form field — adding `course_id` follows the exact same pattern
  - The Textbook interface is used throughout the frontend — adding course_id here makes it available everywhere

  **Acceptance Criteria**:
  - [ ] `cd backend && python -m pytest tests/test_textbooks_import.py -v` → PASS
  - [ ] Import with valid course_id saves both course + course_id on textbook
  - [ ] Import with invalid course_id returns 404
  - [ ] Textbook interface in textbooks.ts includes course_id field

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Import textbook with course_id
    Tool: Bash (curl)
    Preconditions: Backend running, course exists
    Steps:
      1. Get course_id from GET /api/courses
      2. POST /api/textbooks/import -F 'file=@test.pdf' -F 'course_id={course_id}'
      3. GET /api/textbooks/{id} → verify course_id field matches
    Expected Result: Textbook created with correct course_id
    Failure Indicators: course_id null on textbook, 500 error
    Evidence: .sisyphus/evidence/task-4-import-with-course-id.txt

  Scenario: Import with non-existent course_id rejected
    Tool: Bash (curl)
    Preconditions: Backend running
    Steps:
      1. POST /api/textbooks/import -F 'file=@test.pdf' -F 'course_id=nonexistent-uuid'
      2. Verify 404 response
    Expected Result: 404 with error message about course not found
    Failure Indicators: 200 (textbook created), 500 error
    Evidence: .sisyphus/evidence/task-4-invalid-course-id.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(import): add course_id to textbook import flow`
  - Files: `backend/app/routers/textbooks.py`, `frontend/src/api/textbooks.ts`
  - Pre-commit: `cd backend && python -m pytest tests/`

---

- [x] 5. Frontend Courses API Client

  **What to do**:
  - Create `frontend/src/api/courses.ts` following exact pattern from `textbooks.ts`:
    ```typescript
    const BASE_URL = 'http://127.0.0.1:8000'

    export interface Course {
      id: string
      name: string
      created_at: string
      textbook_count: number
      material_count: number
    }

    export async function getCourses(): Promise<Course[]>
    export async function getCourse(id: string): Promise<Course>
    export async function createCourse(name: string): Promise<Course>
    export async function updateCourse(id: string, name: string): Promise<Course>
    export async function deleteCourse(id: string): Promise<void>
    ```
  - Each function uses `fetch()` with proper error handling matching `textbooks.ts` pattern (try body.detail, fallback to status)
  - TDD: Test each function with mocked fetch (vitest mock)

  **Must NOT do**:
  - Do NOT use axios or any HTTP library — use native fetch
  - Do NOT add caching or state management

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Boilerplate API client following established pattern exactly
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4, 6)
  - **Blocks**: Tasks 7, 8, 9, 10, 11
  - **Blocked By**: None (can write against API spec before backend is ready)

  **References**:

  **Pattern References** (existing code to follow):
  - `frontend/src/api/textbooks.ts:1-66` — Complete file — follow this EXACTLY for BASE_URL, error handling, interface style, function signatures

  **WHY Each Reference Matters**:
  - `textbooks.ts` is the ONLY API client in the project — courses.ts must be a near-copy with different types and endpoints

  **Acceptance Criteria**:
  - [ ] File exists: `frontend/src/api/courses.ts`
  - [ ] Exports: getCourses, getCourse, createCourse, updateCourse, deleteCourse
  - [ ] Uses native fetch with proper error handling
  - [ ] Course interface matches backend response shape

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: API client functions are well-typed and exported
    Tool: Bash (TypeScript compiler)
    Preconditions: Frontend project builds
    Steps:
      1. Run: cd frontend && npx tsc --noEmit
      2. Verify no type errors in courses.ts
      3. Verify courses.ts exports all 5 functions
    Expected Result: Zero TypeScript errors, all functions exported
    Failure Indicators: Type errors, missing exports
    Evidence: .sisyphus/evidence/task-5-type-check.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(api): courses frontend API client`
  - Files: `frontend/src/api/courses.ts`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

---

- [x] 6. Frontend University Materials API Client

  **What to do**:
  - Create `frontend/src/api/universityMaterials.ts` following same pattern:
    ```typescript
    export interface UniversityMaterial {
      id: string
      course_id: string
      title: string
      file_type: string
      filepath: string
      created_at: string
    }

    export async function getUniversityMaterials(courseId: string): Promise<UniversityMaterial[]>
    export async function uploadUniversityMaterial(file: File, courseId: string): Promise<UniversityMaterial>
    export async function deleteUniversityMaterial(id: string): Promise<void>
    ```
  - Upload uses FormData (same pattern as `importTextbook`)
  - TDD: Type check passes

  **Must NOT do**:
  - Do NOT add processing status tracking — university materials don't get processed

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small boilerplate API client
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4, 5)
  - **Blocks**: Tasks 9, 11
  - **Blocked By**: None

  **References**:

  **Pattern References** (existing code to follow):
  - `frontend/src/api/textbooks.ts:37-50` — `importTextbook()` FormData upload pattern — follow for uploadUniversityMaterial
  - `frontend/src/api/courses.ts` — (from Task 5) — follow same error handling style

  **Acceptance Criteria**:
  - [ ] File exists: `frontend/src/api/universityMaterials.ts`
  - [ ] Exports: getUniversityMaterials, uploadUniversityMaterial, deleteUniversityMaterial
  - [ ] `cd frontend && npx tsc --noEmit` → zero errors

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: API client type checks cleanly
    Tool: Bash (TypeScript compiler)
    Steps:
      1. Run: cd frontend && npx tsc --noEmit
      2. Verify no type errors in universityMaterials.ts
    Expected Result: Zero TypeScript errors
    Evidence: .sisyphus/evidence/task-6-type-check.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(api): university materials frontend API client`
  - Files: `frontend/src/api/universityMaterials.ts`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

---

- [x] 7. BookshelfPage.tsx Rewrite — 3-Column Layout + HOME_VIEW

  **What to do**:
  - **Delete all existing BookshelfPage.tsx content** (282 lines) and **delete all existing bookshelf.css** (368 lines) — clean slate rewrite
  - Create new BookshelfPage with CSS Grid 3-column layout:
    - Left column (~25%): Course list sidebar with search bar, "+ New Course" button, scrollable course list
    - Middle column (~50%): Scenery placeholder (empty div with class for Task 12) + Study Desk area
    - Right column (~25%): Reserve space PixelPanel with "Coming Soon" text
  - Layout uses CSS Grid: `grid-template-columns: 1fr 2fr 1fr` with gap
  - Settings button: top-right corner, navigates to `/settings` (reuse existing pattern)
  - State machine — `useState<'home' | 'preview'>('home')` for HOME_VIEW / COURSE_PREVIEW_VIEW
  - Course list rendering:
    - Each course is a `div.course-item` with course name + textbook count badge
    - Math Library course has a special icon/tag (e.g., 📚 emoji or CSS-only star)
    - Search bar: `<input>` that filters course list client-side via `.toLowerCase().includes()`
    - Hover: CSS `box-shadow` glow effect on `.course-item:hover`
    - Selection: `useState<string | null>(null)` for `selectedCourseId`. Click sets it. CSS `.course-item.selected` has persistent glow + border.
    - Double-click OR click "Select Course" button: transitions to COURSE_PREVIEW_VIEW
    - Keyboard: `tabIndex={0}`, `onKeyDown` for Enter (select), Space (toggle), Escape (deselect)
  - Action buttons (below course list):
    - "+ New Course" (always visible)
    - "Upload" (visible when course selected, not Math Library)
    - "Delete" (visible when course selected, not Math Library)
    - "Select Course" (visible when course selected)
  - Data fetching: `useEffect` → `getCourses()` on mount. Store in `useState<Course[]>([])`
  - Error handling: display error in a simple text element if API fails
  - CSS in `bookshelf.css`:
    - Use CSS variables from `theme.css` (`--color-*`, `--font-*`, `--space-*`, `--border-pixel*`, `--shadow-pixel*`)
    - Pixel art aesthetic: `font-family: var(--font-primary)` (Press Start 2P)
    - Course item hover glow: `box-shadow: 0 0 8px var(--color-primary)` on hover
    - Course item selected: `border: 2px solid var(--color-primary); box-shadow: 0 0 12px var(--color-primary)`
    - Scrollable course list with custom pixel scrollbar styling
    - `.course-item` text-overflow: ellipsis for long names, `title` attribute for full name
    - Responsive: minimum width enforcement, no column collapse

  **Must NOT do**:
  - Do NOT add react-router routes for view states — HOME_VIEW/COURSE_PREVIEW_VIEW are useState
  - Do NOT add global state management (Redux/Zustand)
  - Do NOT implement Course Preview view — that's Task 11. Just set state to 'preview' and show a placeholder.
  - Do NOT implement upload/delete/create dialogs — those are Tasks 8, 9, 10. Just add button onClick handlers that set dialog open state.
  - Do NOT add pixel art scenery — that's Task 12. Leave the scenery area as an empty placeholder div.
  - Do NOT add progress indicator — that's Task 13.
  - Do NOT touch DeskPage.tsx or App.tsx routes

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Major UI rewrite with CSS Grid layout, hover effects, selection mechanics, pixel art aesthetic
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: CSS Grid layout, hover effects, scrollable lists, responsive design
  - **Skills Evaluated but Omitted**:
    - `playwright`: Not needed in implementation — QA is separate

  **Parallelization**:
  - **Can Run In Parallel**: NO (foundational UI task)
  - **Parallel Group**: Wave 2 (first task, blocks everything)
  - **Blocks**: Tasks 8, 9, 10, 11, 12, 13, 14
  - **Blocked By**: Tasks 1 (schema), 3 (courses API), 5 (courses.ts client)

  **References**:

  **Pattern References** (existing code to follow):
  - `frontend/src/pages/BookshelfPage.tsx:1-50` — Current file to understand what's being replaced (imports, data fetching, state management pattern)
  - `frontend/src/components/pixel/PixelButton.tsx` — PixelButton component with variants (primary/secondary/danger)
  - `frontend/src/components/pixel/PixelPanel.tsx` — PixelPanel container component for the reserve space
  - `frontend/src/components/pixel/PixelDialog.tsx` — PixelDialog for modals (used by Tasks 8, 9, 10)
  - `frontend/src/pages/DeskPage.tsx:1-5` — Navigation target pattern — uses `useNavigate` from react-router-dom

  **API/Type References**:
  - `frontend/src/api/courses.ts` — (from Task 5) — getCourses(), Course interface
  - `frontend/src/api/textbooks.ts:3-10` — Textbook interface (now with course_id)

  **Test References**:
  - `frontend/src/__tests__/BookshelfPage.test.tsx` — Current test file to understand mocking patterns (will be rewritten in Task 14)

  **External References**:
  - CSS theme: `frontend/src/styles/theme.css` — CSS variables to use for all styling
  - CSS reference: `frontend/src/styles/bookshelf.css` — Current file to delete entirely

  **WHY Each Reference Matters**:
  - `BookshelfPage.tsx` shows the existing data fetching + state management pattern (useState + useEffect + fetch) that must be preserved in the rewrite
  - `PixelButton.tsx` shows available variants — use `primary` for '+ New Course', `danger` for Delete
  - `theme.css` is the SINGLE SOURCE for all CSS values — never hardcode colors/fonts/spacing

  **Acceptance Criteria**:
  - [ ] BookshelfPage.tsx renders 3-column layout with CSS Grid
  - [ ] Course list loads from API and displays course names
  - [ ] Search bar filters courses client-side
  - [ ] Hover glow effect works on course items
  - [ ] Click-to-lock selection works with visual feedback
  - [ ] '+ New Course', 'Upload', 'Delete', 'Select Course' buttons render correctly
  - [ ] Settings button top-right navigates to /settings
  - [ ] Reserve space shows 'Coming Soon' PixelPanel
  - [ ] Math Library course cannot be deleted (button hidden/disabled)
  - [ ] `cd frontend && npx tsc --noEmit` → zero errors

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 3-column layout renders correctly
    Tool: Playwright (playwright skill)
    Preconditions: Frontend dev server running (npm run dev), backend running with at least Math Library course
    Steps:
      1. Navigate to http://localhost:5173/
      2. Wait for .bookshelf-grid CSS grid container to render
      3. Assert left column (.course-sidebar) exists
      4. Assert middle column (.scenery-area) exists
      5. Assert right column (.reserve-space) exists
      6. Assert CSS grid-template-columns is applied
      7. Screenshot the full page
    Expected Result: 3 columns visible, course list on left, scenery placeholder in middle, 'Coming Soon' on right
    Failure Indicators: Single column layout, missing columns, CSS grid not applied
    Evidence: .sisyphus/evidence/task-7-3-column-layout.png

  Scenario: Course list hover glow + selection
    Tool: Playwright (playwright skill)
    Preconditions: Frontend + backend running, 2+ courses exist
    Steps:
      1. Navigate to http://localhost:5173/
      2. Hover over first .course-item
      3. Assert box-shadow CSS property contains glow value
      4. Click first .course-item
      5. Assert .course-item.selected class is applied
      6. Assert 'Upload' and 'Delete' buttons become visible/enabled
      7. Click same item again — verify still selected (click-to-lock, not toggle)
      8. Screenshot
    Expected Result: Hover shows glow, click locks selection with persistent highlight, action buttons appear
    Failure Indicators: No visual feedback on hover, selection doesn't persist, buttons don't appear
    Evidence: .sisyphus/evidence/task-7-hover-selection.png

  Scenario: Search filters course list
    Tool: Playwright (playwright skill)
    Preconditions: Frontend running, 3+ courses exist including 'Math Library'
    Steps:
      1. Navigate to http://localhost:5173/
      2. Count visible .course-item elements — expect 3+
      3. Type 'math' into .course-search-input
      4. Count visible .course-item elements — expect 1 ('Math Library')
      5. Clear search input
      6. Count visible .course-item elements — expect 3+ (all restored)
    Expected Result: Search filters list in real-time, clearing restores all
    Failure Indicators: Filter doesn't work, items don't restore on clear
    Evidence: .sisyphus/evidence/task-7-search-filter.png
  ```

  **Evidence to Capture:**
  - [ ] Screenshots of 3-column layout, hover state, selection state, search filtering
  - [ ] TypeScript compilation output

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(ui): BookshelfPage rewrite — 3-column layout with course list, search, hover/selection`
  - Files: `frontend/src/pages/BookshelfPage.tsx`, `frontend/src/styles/bookshelf.css`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

---

- [x] 8. Course Creation Dialog — '+ New Course' Flow

  **What to do**:
  - Add course creation dialog to BookshelfPage using PixelDialog:
    - State: `useState<boolean>(false)` for `isCreateDialogOpen`
    - State: `useState<string>('')` for `newCourseName`
    - '+ New Course' button `onClick` sets `isCreateDialogOpen = true`
    - Dialog content: text input for course name + 'Create' button + 'Cancel' button
    - On submit: call `createCourse(newCourseName)` from courses.ts API client
    - On success: close dialog, refresh course list, select the newly created course
    - On error (409 duplicate): show error message in dialog (not alert())
    - On error (other): show error message
    - Input validation: trim whitespace, reject empty names, min 1 char
    - Enter key submits, Escape closes dialog
  - TDD: Test dialog opens when button clicked
  - TDD: Test successful creation refreshes list
  - TDD: Test duplicate name shows error in dialog

  **Must NOT do**:
  - Do NOT use window.prompt() or window.alert() — use PixelDialog only
  - Do NOT add course fields beyond name (no color, description, icon)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple modal with one input, using existing PixelDialog component
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 9, 10)
  - **Blocks**: Task 14
  - **Blocked By**: Tasks 3, 5, 7

  **References**:

  **Pattern References** (existing code to follow):
  - `frontend/src/components/pixel/PixelDialog.tsx:4-9` — PixelDialog props (isOpen, onClose, title, children)
  - `frontend/src/components/pixel/PixelButton.tsx:5` — PixelButton variants (primary for Create, secondary for Cancel)
  - `frontend/src/api/courses.ts` — (from Task 5) — createCourse() function

  **WHY Each Reference Matters**:
  - PixelDialog is a simple container — all form content goes in children slot
  - Must use existing PixelButton variants for visual consistency

  **Acceptance Criteria**:
  - [ ] '+ New Course' button opens PixelDialog
  - [ ] Dialog has text input + Create + Cancel buttons
  - [ ] Successful creation refreshes course list
  - [ ] Duplicate name shows inline error (not alert)
  - [ ] Enter submits, Escape closes
  - [ ] Empty name rejected with validation message

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Create a new course
    Tool: Playwright (playwright skill)
    Preconditions: Frontend + backend running
    Steps:
      1. Navigate to http://localhost:5173/
      2. Click '+ New Course' button (.create-course-btn or [data-testid="create-course-btn"])
      3. Wait for PixelDialog to open (assert .pixel-dialog visible)
      4. Type 'MECH0089' into course name input
      5. Click 'Create' button
      6. Wait for dialog to close
      7. Assert 'MECH0089' appears in course list
    Expected Result: Course created, dialog closes, list refreshed showing new course
    Failure Indicators: Dialog doesn't close, course not in list, error shown
    Evidence: .sisyphus/evidence/task-8-create-course.png

  Scenario: Duplicate name shows error
    Tool: Playwright (playwright skill)
    Preconditions: 'MECH0089' course already exists
    Steps:
      1. Click '+ New Course' button
      2. Type 'MECH0089' into name input
      3. Click 'Create'
      4. Assert error message visible in dialog (not a browser alert)
      5. Assert dialog is still open (not closed)
    Expected Result: Error message shown inline, dialog remains open for correction
    Failure Indicators: Dialog closes, browser alert pops up, no error shown
    Evidence: .sisyphus/evidence/task-8-duplicate-error.png
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(ui): course creation dialog with validation`
  - Files: `frontend/src/pages/BookshelfPage.tsx`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

---

- [x] 9. Upload Dialog — Textbook vs University Material Choice

  **What to do**:
  - Add upload dialog to BookshelfPage using PixelDialog:
    - State: `useState<boolean>(false)` for `isUploadDialogOpen`
    - State: `useState<'choice' | 'textbook' | 'material'>('choice')` for dialog step
    - 'Upload' button `onClick` sets `isUploadDialogOpen = true`, resets step to 'choice'
    - **Step 1 (choice)**: Dialog shows two large PixelButtons: "📚 Textbook" and "📄 University Material"
    - **Step 2a (textbook)**: File input with `accept=".pdf"`. On file select: call `importTextbook(file, undefined, selectedCourseId)` from textbooks.ts. Close dialog. Start polling for progress (Task 13 handles display).
    - **Step 2b (material)**: File input with `accept=".pdf,.pptx,.docx,.txt,.md,.xlsx"`. On file select: call `uploadUniversityMaterial(file, selectedCourseId)` from universityMaterials.ts. Close dialog. Refresh course data.
    - Back button in Step 2 returns to Step 1
    - Escape closes dialog at any step
    - Hidden file input triggered by a visible PixelButton "Choose File"
  - TDD: Test dialog opens with choice step
  - TDD: Test selecting "Textbook" shows PDF file input
  - TDD: Test selecting "University Material" shows multi-type file input

  **Must NOT do**:
  - Do NOT process university materials — upload and store only
  - Do NOT show upload progress in the dialog — dialog closes immediately, progress shows on course bar (Task 13)
  - Do NOT allow upload to Math Library (Upload button should not appear when Math Library is selected)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Multi-step dialog with file inputs, using existing PixelDialog
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 8, 10)
  - **Blocks**: Task 14
  - **Blocked By**: Tasks 3, 4, 5, 6, 7

  **References**:

  **Pattern References** (existing code to follow):
  - `frontend/src/components/pixel/PixelDialog.tsx` — PixelDialog props for the dialog container
  - `frontend/src/pages/BookshelfPage.tsx:104-133` — (OLD file) Existing upload + polling pattern — reference for how to trigger importTextbook and poll status
  - `frontend/src/api/textbooks.ts:37-50` — `importTextbook()` function signature
  - `frontend/src/api/universityMaterials.ts` — (from Task 6) `uploadUniversityMaterial()` function

  **WHY Each Reference Matters**:
  - The old BookshelfPage upload pattern shows how file input + importTextbook + status polling are wired together — the new dialog wraps this same flow
  - Both API clients (textbooks.ts, universityMaterials.ts) define the exact upload function signatures to call

  **Acceptance Criteria**:
  - [ ] Upload button opens dialog with Textbook/Material choice
  - [ ] Selecting Textbook shows PDF-only file input
  - [ ] Selecting University Material shows multi-type file input (.pdf,.pptx,.docx,.txt,.md,.xlsx)
  - [ ] File upload triggers correct API call (importTextbook or uploadUniversityMaterial)
  - [ ] Dialog closes after file selection
  - [ ] Upload button hidden/disabled when Math Library selected

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Upload textbook to a course
    Tool: Playwright (playwright skill)
    Preconditions: Frontend + backend running, non-Math-Library course exists and is selected
    Steps:
      1. Navigate to http://localhost:5173/
      2. Click a course (not Math Library) to select it
      3. Click 'Upload' button
      4. Assert PixelDialog opens with two choice buttons
      5. Click 'Textbook' button
      6. Assert file input has accept=".pdf"
      7. Upload a test PDF file via the file input
      8. Assert dialog closes
    Expected Result: Dialog presents choice, textbook path accepts PDF only, upload triggers API call
    Failure Indicators: Dialog doesn't open, wrong file types accepted, dialog doesn't close
    Evidence: .sisyphus/evidence/task-9-upload-textbook.png

  Scenario: Upload university material accepts multiple types
    Tool: Playwright (playwright skill)
    Preconditions: Frontend + backend running, course selected
    Steps:
      1. Click 'Upload' button
      2. Click 'University Material' button
      3. Assert file input accept attribute includes .pdf,.pptx,.docx,.txt,.md,.xlsx
    Expected Result: File input accepts all specified formats
    Failure Indicators: File input only accepts .pdf
    Evidence: .sisyphus/evidence/task-9-upload-material.png
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(ui): upload dialog — textbook vs university material choice`
  - Files: `frontend/src/pages/BookshelfPage.tsx`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

---

- [x] 10. Delete Confirmation Dialog — Prevent Accidental Deletion

  **What to do**:
  - Add delete confirmation dialog to BookshelfPage using PixelDialog:
    - State: `useState<boolean>(false)` for `isDeleteDialogOpen`
    - 'Delete' button `onClick` sets `isDeleteDialogOpen = true`
    - Dialog title: "Delete Course"
    - Dialog content: "Are you sure you want to delete '{courseName}'? This will permanently remove all textbooks, university materials, and associated data."
    - Two buttons: "Cancel" (secondary) and "Delete" (danger variant)
    - On confirm: call `deleteCourse(selectedCourseId)` from courses.ts. On success: close dialog, deselect course, refresh course list.
    - On error: show error message in dialog (e.g., 409 if active uploads, 403 if Math Library)
    - Delete button should show loading state during API call (disable button, show '...')
    - Escape closes dialog (same as Cancel)
  - Delete button hidden when Math Library is selected (matching Upload behavior)
  - TDD: Test dialog opens when Delete clicked
  - TDD: Test confirm triggers deleteCourse API call
  - TDD: Test cancel closes dialog without deleting

  **Must NOT do**:
  - Do NOT use window.confirm() — use PixelDialog only
  - Do NOT allow deleting Math Library (button hidden, plus 403 backend safety)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple confirmation dialog with two buttons
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 8, 9)
  - **Blocks**: Task 14
  - **Blocked By**: Tasks 3, 5, 7

  **References**:

  **Pattern References** (existing code to follow):
  - `frontend/src/components/pixel/PixelDialog.tsx` — PixelDialog container
  - `frontend/src/components/pixel/PixelButton.tsx:5` — `danger` variant for delete button
  - `frontend/src/api/courses.ts` — (from Task 5) `deleteCourse()` function

  **WHY Each Reference Matters**:
  - PixelButton `danger` variant provides the red destructive action styling
  - deleteCourse() calls the cascade delete endpoint which handles everything server-side

  **Acceptance Criteria**:
  - [ ] Delete button opens confirmation dialog
  - [ ] Dialog shows course name and warning text
  - [ ] Cancel closes without deleting
  - [ ] Confirm deletes course and refreshes list
  - [ ] Delete button hidden when Math Library selected
  - [ ] Error from API shown in dialog (not alert)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Delete a course with confirmation
    Tool: Playwright (playwright skill)
    Preconditions: Frontend + backend running, test course exists
    Steps:
      1. Navigate to http://localhost:5173/
      2. Click test course to select it
      3. Click 'Delete' button
      4. Assert confirmation dialog opens with course name
      5. Assert warning text mentions 'permanently remove'
      6. Click 'Delete' button in dialog
      7. Wait for dialog to close
      8. Assert test course no longer in course list
    Expected Result: Course deleted after confirmation, list updated
    Failure Indicators: Course still present, dialog doesn't close, error
    Evidence: .sisyphus/evidence/task-10-delete-confirm.png

  Scenario: Cancel prevents deletion
    Tool: Playwright (playwright skill)
    Preconditions: Frontend + backend running, course selected
    Steps:
      1. Click 'Delete' button
      2. Assert dialog opens
      3. Click 'Cancel'
      4. Assert dialog closes
      5. Assert course still present in list
    Expected Result: No deletion occurred, course intact
    Failure Indicators: Course deleted despite cancel
    Evidence: .sisyphus/evidence/task-10-delete-cancel.png
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(ui): delete confirmation dialog with cascade warning`
  - Files: `frontend/src/pages/BookshelfPage.tsx`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

---

- [ ] 11. Course Preview View — 3 Sub-Panels + "Begin Study" Navigation

  **What to do**:
  - Implement COURSE_PREVIEW_VIEW in BookshelfPage (when `viewState === 'preview'`):
    - Replace the middle + right columns content with Course Preview layout
    - Left column stays as course list (with selected course highlighted)
    - Middle + right columns become 3 sub-panels in a horizontal layout:
      - **Panel 1: Textbooks** — Lists textbooks in the selected course
        - Each textbook item shows: title, processed status indicator
        - Click on a textbook to select it for study
        - "Begin Study" button (PixelButton primary) — navigates to `/desk/:textbookId` using `useNavigate()`
        - "Begin Study" disabled with tooltip if no textbook selected
        - If course has 0 textbooks: show empty state message "No textbooks yet. Upload one to get started."
      - **Panel 2: University Content** — Lists university materials in the selected course
        - Each item shows: title, file_type badge, created_at date
        - No actions in v1 (just a list for reference)
        - If 0 materials: show empty state "No university materials uploaded yet."
      - **Panel 3: TBD** — Empty PixelPanel with "More features coming soon" text
    - Back button (PixelButton secondary) at the top: returns to HOME_VIEW (`setViewState('home')`)
    - Course name displayed as a header above the panels
  - Data fetching when entering preview: `useEffect` that fires when `viewState === 'preview' && selectedCourseId` changes → call `getTextbooks(selectedCourseId)` + `getUniversityMaterials(selectedCourseId)`
  - Store results in `useState` for textbooks + materials lists
  - Keyboard: Escape returns to HOME_VIEW
  - TDD: Test preview renders 3 panels
  - TDD: Test Begin Study navigates to /desk/:textbookId
  - TDD: Test empty states display correct messages

  **Must NOT do**:
  - Do NOT add actions to university materials (no open, preview, delete — just list them)
  - Do NOT modify DeskPage.tsx
  - Do NOT add new routes — this is still at `/`
  - Do NOT add ability to remove individual textbooks from preview (that's managing, not previewing)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Multi-panel UI layout with data fetching, navigation, empty states, and interaction
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Multi-panel layout, empty states, navigation patterns

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Wave 2 completion)
  - **Parallel Group**: Wave 3 (with Tasks 12, 13, 14)
  - **Blocks**: Task 14
  - **Blocked By**: Tasks 3, 5, 6, 7

  **References**:

  **Pattern References** (existing code to follow):
  - `frontend/src/pages/BookshelfPage.tsx` — (from Task 7) — The rewritten file where preview view goes
  - `frontend/src/pages/DeskPage.tsx:1-10` — Shows how useNavigate() is used — pattern for "Begin Study" navigation
  - `frontend/src/components/pixel/PixelPanel.tsx` — Container for each sub-panel

  **API/Type References**:
  - `frontend/src/api/textbooks.ts:28-35` — `getTextbooks()` — filter by course to get textbooks for selected course
  - `frontend/src/api/universityMaterials.ts` — (from Task 6) `getUniversityMaterials(courseId)`
  - `frontend/src/api/textbooks.ts:3-10` — Textbook interface with course_id field

  **WHY Each Reference Matters**:
  - DeskPage.tsx shows the exact `useNavigate()` + `/desk/${textbookId}` pattern for "Begin Study"
  - getTextbooks() already supports filtering — but needs course_id filter (not course name). May need to add this parameter or filter client-side by course_id.

  **Acceptance Criteria**:
  - [ ] Double-click course transitions to COURSE_PREVIEW_VIEW
  - [ ] Preview shows 3 sub-panels: Textbooks, University Content, TBD
  - [ ] Textbooks panel lists textbooks for selected course
  - [ ] University Content panel lists materials for selected course
  - [ ] "Begin Study" navigates to `/desk/:textbookId`
  - [ ] "Begin Study" disabled when no textbook selected
  - [ ] Empty states shown for 0 textbooks / 0 materials
  - [ ] Back button returns to HOME_VIEW
  - [ ] Escape returns to HOME_VIEW

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Course Preview shows textbooks and materials
    Tool: Playwright (playwright skill)
    Preconditions: Frontend + backend running, course exists with 1+ textbook and 1+ material
    Steps:
      1. Navigate to http://localhost:5173/
      2. Double-click on the test course
      3. Wait for COURSE_PREVIEW_VIEW to render
      4. Assert 3 sub-panels visible (.textbooks-panel, .materials-panel, .tbd-panel)
      5. Assert textbook title appears in textbooks panel
      6. Assert material title appears in materials panel
      7. Assert TBD panel shows 'More features coming soon'
      8. Screenshot
    Expected Result: All 3 panels populated correctly
    Failure Indicators: Panels empty, wrong data, layout broken
    Evidence: .sisyphus/evidence/task-11-course-preview.png

  Scenario: Begin Study navigates to DeskPage
    Tool: Playwright (playwright skill)
    Preconditions: Course Preview visible with textbooks
    Steps:
      1. Click on a textbook in the textbooks panel to select it
      2. Click 'Begin Study' button
      3. Assert URL changed to /desk/{textbookId}
      4. Assert DeskPage content renders
    Expected Result: Navigation to DeskPage with correct textbook ID
    Failure Indicators: URL unchanged, DeskPage doesn't load, wrong textbook
    Evidence: .sisyphus/evidence/task-11-begin-study.png

  Scenario: Empty course shows empty states
    Tool: Playwright (playwright skill)
    Preconditions: Empty course exists (0 textbooks, 0 materials)
    Steps:
      1. Double-click empty course
      2. Assert textbooks panel shows 'No textbooks yet' message
      3. Assert materials panel shows 'No university materials' message
      4. Assert 'Begin Study' button is disabled
    Expected Result: Empty states displayed, Begin Study disabled
    Failure Indicators: Panels show loading forever, button enabled with no textbook
    Evidence: .sisyphus/evidence/task-11-empty-state.png
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(ui): course preview — 3 sub-panels with begin study navigation`
  - Files: `frontend/src/pages/BookshelfPage.tsx`, `frontend/src/styles/bookshelf.css`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

---

- [ ] 12. CSS Pixel Art Scenery Component

  **What to do**:
  - Create a pixel art scenery in the middle column of HOME_VIEW using **CSS-only** techniques:
    - Scene: A study desk with a small lamp, against a window showing a night sky with stars
    - Built entirely with CSS `box-shadow` technique (single-div pixel art) or layered `div` elements with CSS backgrounds
    - Place in the `.scenery-area` div from Task 7
    - CSS goes in `bookshelf.css` (or a new `scenery.css` imported by BookshelfPage)
    - Use CSS variables from `theme.css` for colors where applicable
    - Scene should be static (no animation beyond simple CSS transitions like a subtle lamp glow)
    - Responsive: scene scales or centers within the middle column
    - Must NOT use any image files (.png, .jpg, .svg, .gif)
    - Fallback: If CSS art is too complex, a simpler pixel-style border decoration with text "Your Study Space" is acceptable
  - TDD: Test that scenery container renders (has correct class)

  **Must NOT do**:
  - Do NOT use image files or SVGs — CSS only
  - Do NOT add JavaScript animation (no requestAnimationFrame, no setInterval for animation)
  - Do NOT make scenery change based on context (deferred to v2)
  - Do NOT spend excessive time on scenery detail — a simple recognizable desk scene is sufficient

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: CSS pixel art is visual design work requiring creative CSS skills
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: CSS creative techniques, box-shadow pixel art

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 13, 14)
  - **Blocks**: Task 14
  - **Blocked By**: Task 7

  **References**:

  **External References**:
  - CSS box-shadow pixel art technique: Search "CSS box-shadow pixel art" for examples — single div with multiple box-shadows creating a pixel grid
  - NES.css inspiration: `https://nostalgic-css.github.io/NES.css/` — pixel art CSS patterns

  **Pattern References**:
  - `frontend/src/styles/theme.css:4-62` — CSS variables for colors, fonts, spacing
  - `frontend/src/styles/bookshelf.css` — (from Task 7) Where scenery CSS goes

  **WHY Each Reference Matters**:
  - `theme.css` provides the color palette — scenery should use `--color-bg-dark`, `--color-primary`, `--color-accent` etc. for consistency

  **Acceptance Criteria**:
  - [ ] Scenery renders in middle column of HOME_VIEW
  - [ ] No image files used — CSS only
  - [ ] Scene is recognizable as a study desk/workspace
  - [ ] Uses theme.css CSS variables for colors
  - [ ] No JavaScript animation

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Pixel art scenery renders without images
    Tool: Playwright (playwright skill)
    Preconditions: Frontend running
    Steps:
      1. Navigate to http://localhost:5173/
      2. Assert .scenery-area element exists and is visible
      3. Assert NO <img> or <svg> elements inside .scenery-area
      4. Assert .scenery-area has CSS content (box-shadow or background)
      5. Screenshot the scenery area
    Expected Result: Visual pixel art scene visible, no image elements in DOM
    Failure Indicators: Empty area, broken images, SVG elements present
    Evidence: .sisyphus/evidence/task-12-pixel-scenery.png
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(ui): CSS pixel art study desk scenery`
  - Files: `frontend/src/styles/bookshelf.css` (or `frontend/src/styles/scenery.css`)
  - Pre-commit: `cd frontend && npx tsc --noEmit`

---

- [ ] 13. Course Bar Progress Indicator — Upload Progress on Course Item

  **What to do**:
  - Add upload progress tracking to course items in the course list:
    - When a textbook is being uploaded/processed for a course, show progress on that course's list item
    - Reuse existing polling pattern from old BookshelfPage (setInterval + getImportStatus)
    - State: `useState<Record<string, {progress: number, step: string}>>({})` mapping courseId → progress
    - When upload starts (from Task 9): store the jobId associated with the courseId
    - Poll `getImportStatus(jobId)` every 2 seconds
    - Display progress as a background fill on the `.course-item` div:
      - CSS: `.course-item` gets a `::before` pseudo-element with `width: {progress}%` and a semi-transparent color fill
      - Alternatively: CSS `background: linear-gradient(to right, var(--color-primary-faded) {progress}%, transparent {progress}%)`
    - Show step text below the course name (small font, truncated): e.g., "Extracting text..."
    - When complete: remove progress state, refresh course data to update textbook_count
    - When error: show error indicator on course item (red border? small error icon?)
  - TDD: Test that progress state updates course item style

  **Must NOT do**:
  - Do NOT add cancel upload functionality
  - Do NOT show percentage text on the progress bar — just visual fill
  - Do NOT add progress for university material uploads (they're instant — just file save)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Reusing existing polling pattern + CSS progress styling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 12, 14)
  - **Blocks**: Task 14
  - **Blocked By**: Task 7

  **References**:

  **Pattern References** (existing code to follow):
  - OLD `frontend/src/pages/BookshelfPage.tsx:104-133` — The original polling pattern (setInterval, getImportStatus, clearInterval on complete/error). This exact pattern should be adapted.
  - `frontend/src/api/textbooks.ts:52-56` — `getImportStatus()` function
  - `frontend/src/api/textbooks.ts:18-26` — `ImportStatus` interface with progress + step fields

  **WHY Each Reference Matters**:
  - The original BookshelfPage had a working progress polling system — same logic, just displayed differently (on course item instead of separate bar)

  **Acceptance Criteria**:
  - [ ] During textbook upload, course item shows progress fill
  - [ ] Step text displays below course name during processing
  - [ ] Progress fill grows as processing advances
  - [ ] Completion removes progress indicator and refreshes course data
  - [ ] Error shows error indicator on course item

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Course item shows upload progress
    Tool: Playwright (playwright skill)
    Preconditions: Frontend + backend running, course selected
    Steps:
      1. Upload a textbook to selected course (via upload dialog)
      2. Observe the course item in the sidebar
      3. Assert course item has progress fill (check CSS background or ::before width)
      4. Assert step text is visible (e.g., 'Extracting text...')
      5. Wait for processing to complete (up to 60s timeout)
      6. Assert progress fill is gone
      7. Assert textbook_count on course item increased
      8. Screenshot during progress + screenshot after completion
    Expected Result: Visual progress on course item during upload, clean state after
    Failure Indicators: No visual progress, progress stuck, step text missing
    Evidence: .sisyphus/evidence/task-13-progress-during.png, .sisyphus/evidence/task-13-progress-complete.png
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(ui): course bar progress indicator during textbook upload`
  - Files: `frontend/src/pages/BookshelfPage.tsx`, `frontend/src/styles/bookshelf.css`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

---

- [ ] 14. BookshelfPage.test.tsx Rewrite — Full Test Coverage

  **What to do**:
  - Delete existing `frontend/src/__tests__/BookshelfPage.test.tsx` entirely and rewrite for the new BookshelfPage:
  - Test cases (minimum):
    - Renders 3-column layout (grid container with 3 children)
    - Loads and displays courses from API (mock getCourses)
    - Search bar filters courses (type text, verify filtered list)
    - Click course selects it (verify .selected class)
    - Double-click course transitions to COURSE_PREVIEW_VIEW
    - '+ New Course' button opens creation dialog
    - Course creation via dialog calls createCourse API (mock)
    - 'Upload' button opens upload dialog with choice step
    - Selecting 'Textbook' in upload dialog shows PDF file input
    - Selecting 'University Material' shows multi-type file input
    - 'Delete' button opens confirmation dialog
    - Delete confirmation calls deleteCourse API (mock)
    - Cancel in delete dialog doesn't trigger API call
    - COURSE_PREVIEW_VIEW shows 3 sub-panels
    - 'Begin Study' navigates to /desk/:textbookId
    - 'Begin Study' disabled when no textbook selected
    - Back button returns to HOME_VIEW
    - Escape key returns to HOME_VIEW from preview
    - Math Library course: Upload + Delete buttons hidden
    - Settings button navigates to /settings
    - Empty course list shows appropriate message
    - Reserve space panel shows 'Coming Soon'
  - Mock all API calls (getCourses, createCourse, deleteCourse, getTextbooks, getUniversityMaterials, importTextbook, uploadUniversityMaterial)
  - Use React Testing Library for rendering + interaction
  - Use vitest for test runner

  **Must NOT do**:
  - Do NOT test CSS visual appearance — that's Playwright (F3)
  - Do NOT test backend API logic — all API calls are mocked
  - Do NOT leave any test from old BookshelfPage.test.tsx

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Comprehensive test file covering all features with mocking
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on all Wave 2+3 implementation tasks)
  - **Parallel Group**: Wave 3 (after Tasks 7-13)
  - **Blocks**: None
  - **Blocked By**: Tasks 7, 8, 9, 10, 11, 12, 13

  **References**:

  **Pattern References** (existing code to follow):
  - `frontend/src/__tests__/BookshelfPage.test.tsx` — Current test file — reference for mocking patterns, then DELETE entirely
  - `frontend/src/__tests__/DeskPage.test.tsx` — Another test file showing React Testing Library patterns (render, screen, fireEvent, waitFor)
  - `frontend/src/__tests__/SettingsPage.test.tsx` — Test pattern for page components with API mocking

  **Test References**:
  - `frontend/src/__tests__/pixel-components.test.tsx` — Tests for PixelButton, PixelPanel, PixelDialog — shows how to test these components

  **WHY Each Reference Matters**:
  - Existing test files show the project's testing patterns: how fetch is mocked, how components are rendered, how user interactions are simulated
  - pixel-components.test.tsx specifically shows how PixelDialog is tested — important for dialog tests

  **Acceptance Criteria**:
  - [ ] `cd frontend && npx vitest run src/__tests__/BookshelfPage.test.tsx` → PASS (20+ tests)
  - [ ] All major features covered: CRUD, dialogs, navigation, search, selection, keyboard
  - [ ] No references to old BookSpine component
  - [ ] All API calls properly mocked

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All BookshelfPage tests pass
    Tool: Bash (vitest)
    Preconditions: Frontend dependencies installed
    Steps:
      1. Run: cd frontend && npx vitest run src/__tests__/BookshelfPage.test.tsx --reporter=verbose
      2. Verify all tests pass
      3. Verify test count >= 20
    Expected Result: 20+ tests passing, 0 failures
    Failure Indicators: Any test failure, fewer than 20 tests
    Evidence: .sisyphus/evidence/task-14-test-results.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `test(ui): complete BookshelfPage test rewrite for course-centric layout`
  - Files: `frontend/src/__tests__/BookshelfPage.test.tsx`
  - Pre-commit: `cd frontend && npx vitest run src/__tests__/BookshelfPage.test.tsx`

---
## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `npx vitest run` + `python -m pytest`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp). Verify CSS uses only variables from theme.css.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill)
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (create course → upload textbook → preview → begin study). Test edge cases: empty state, long names, rapid clicks, delete during upload blocked. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1 commit**: `feat(backend): courses + university materials schema, CRUD router, API clients` — All Wave 1 files
- **Wave 2 commit**: `feat(ui): home screen 3-column layout, course creation, upload + delete dialogs` — All Wave 2 files
- **Wave 3 commit**: `feat(ui): course preview, pixel art scenery, progress indicator, tests` — All Wave 3 files

---

## Success Criteria

### Verification Commands
```bash
cd backend && python -m pytest tests/test_courses.py -v  # Expected: ALL PASS
cd frontend && npx vitest run src/__tests__/BookshelfPage.test.tsx  # Expected: ALL PASS
curl -s http://localhost:8000/api/courses | python -m json.tool  # Expected: JSON array with Math Library course
curl -s -X POST http://localhost:8000/api/courses -H "Content-Type: application/json" -d '{"name":"Test Course"}'  # Expected: 200 with UUID
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All pytest tests pass
- [ ] All vitest tests pass
- [ ] Playwright screenshots captured for all views
- [ ] Math Library course auto-created and non-deletable
- [ ] Upload dialog shows both options with correct file type filters
- [ ] Delete confirmation prevents accidental deletion
- [ ] CSS scenery renders without image assets
