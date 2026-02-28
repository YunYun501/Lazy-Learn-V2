# Learnings — Home Screen Redesign

## [2026-02-28] Session Start

### Codebase Conventions
- `courses.id` is TEXT (UUID) — ALL FK columns referencing it must be TEXT, never INTEGER
- No migration framework — use `ALTER TABLE` with `try/except sqlite3.OperationalError` for idempotency
- `PRAGMA foreign_keys` was NEVER enabled — cascade delete is application-level
- `textbooks.course` TEXT column stores course NAME (not ID) — KEEP IT, add `course_id TEXT` alongside
- Storage pattern: `get_storage()` factory per request in routers (see `textbooks.py:13-19`)
- Background tasks: `_job_status` dict + `BackgroundTasks` (see `textbooks.py:44-80`)
- `conversations.course_id` TEXT column already exists in schema

### Frontend Conventions
- `const BASE_URL = 'http://127.0.0.1:8000'` in all API clients (NOT localhost)
- Error handling in API clients: try `body.detail`, fallback to `Server error ${res.status}` (see `textbooks.ts:45-48`)
- Pixel art aesthetic: "Press Start 2P" font via `var(--font-primary)` CSS variable
- CSS variables: all from `theme.css` — `--color-*`, `--font-*`, `--space-*`, `--border-pixel*`, `--shadow-pixel*`
- No global state management — useState + useEffect only
- PixelDialog props: `isOpen, onClose, title, children` — content goes in children slot
- PixelButton variants: `primary | secondary | danger`
- `conversations.course_id` TEXT column already exists in schema

### Key File Locations
- `backend/app/services/storage.py` — MetadataStore (all DB operations)
- `backend/app/routers/textbooks.py` — Template router pattern
- `frontend/src/api/textbooks.ts` — Template API client pattern
- `frontend/src/components/pixel/PixelDialog.tsx` — Modal component
- `frontend/src/components/pixel/PixelButton.tsx` — Button variants
- `frontend/src/styles/theme.css` — ALL CSS variables

## [2026-02-28] Schema Migration Complete

### Implementation Details
- `university_materials` table created with: id, course_id, title, file_type, filepath, created_at
- `textbooks.course_id TEXT` column added via idempotent ALTER TABLE in initialize()
- Math Library auto-created via INSERT OR IGNORE with stable name-based uniqueness
- All 8 new MetadataStore methods implemented following existing async/aiosqlite patterns
- Cascade delete uses Path-based file deletion (no filesystem.py helpers needed)

### Test Coverage
- 10 tests in test_courses_storage.py all passing
- Tests verify: idempotency, table creation, column existence, Math Library creation, CRUD operations, cascade delete
- Async fixture pattern matches test_storage.py conventions

### Key Patterns Confirmed
- `INSERT OR IGNORE` with UNIQUE constraint prevents duplicate Math Library
- Cascade delete: textbooks → chapters → university_materials → course (order matters)
- All methods use `db.row_factory = aiosqlite.Row` for dict conversion
- No foreign key constraints enabled (application-level cascade)

## [2026-02-28] University Materials Router + Textbook course_id

### Implementation Details
- `university_materials.py` router: upload/list/delete with ALLOWED_EXTENSIONS validation
- `get_university_material(material_id)` added to MetadataStore (needed by DELETE endpoint)
- File storage path: `settings.DATA_DIR / "university_materials" / course_id / {uuid}_{filename}`
- `textbooks.py` import: added `course_id: Optional[str] = Form(None)` + validation + `assign_textbook_to_course` call
- `main.py`: `university_materials` added to both import and `include_router` calls

### Test Patterns
- Use `asyncio.get_event_loop().run_until_complete()` for sync pre-setup in fixtures (pytest-asyncio not needed for HTTP tests)
- `monkeypatch.setattr(module, "get_storage", fn)` patches the router's local function reference
- `monkeypatch.setattr(module, "settings", FakeSettings)` patches DATA_DIR for file storage
- FakeSettings: simple class with `DATA_DIR = tmp_path` attribute
- File upload in TestClient: `files={"file": ("name.pdf", b"content", "mime")}`

### Gotcha
- `replace` with single `pos` only replaces ONE line — use `pos`+`end` range for multi-line function signatures


## [2026-02-28] Task 7 — BookshelfPage Rewrite

### Implementation Details
- `BookshelfPage.tsx` rewritten: 333 lines → 194 lines, no BookSpine component
- Imports: `getCourses, type Course` from `../api/courses`, `PixelButton` + `PixelPanel` from `../components/pixel`
- Dialog state vars declared with `void` suppression: `void isCreateDialogOpen` etc. prevents TS unused-var error
- `isMathLibrary` check: `selectedCourse?.name === 'Math Library'` — name-based, matches Math Library auto-created in Task 1
- `course.id` is `string` (UUID) — `selectedCourseId` state is `string | null`
- `PixelPanel` accepts `className` prop — confirmed by reading component source

### CSS Patterns
- `bookshelf-grid`: `grid-template-columns: 1fr 2fr 1fr` — left sidebar | scenery | reserve space
- `padding-top: calc(var(--space-6) + 40px)` — extra room for absolute-positioned settings button
- `course-sidebar`: `overflow: hidden` on container, `flex: 1` + `overflow-y: auto` on `.course-list` for scrollable list
- `sidebar-actions`: `flex-shrink: 0` prevents action buttons from being squeezed out
- `box-sizing: border-box` on `course-search-input` — prevents width overflow in flex column

### Gotchas
- `void expr` pattern used to suppress TS `noUnusedLocals` for dialog state vars (not `// @ts-ignore`)
- `--transition-fast: 0ms` — pixel art theme has zero-duration transitions (instant state changes)

## [2026-02-28] Task 11 — COURSE_PREVIEW_VIEW

### Implementation Details
- `getTextbooks()` filters by course NAME via query string, NOT course_id — must call bare `getTextbooks()` and filter client-side: `all.filter(t => t.course_id === selectedCourseId)`
- `getUniversityMaterials(courseId)` works directly with UUID — no client-side filtering needed
- PixelPanel accepts `className` prop — stack with custom panel classes (.textbooks-panel etc.) for flex layout override
- Sidebar is duplicated in preview JSX (not extracted to component) — straightforward, avoids premature abstraction
- Escape key: global `useEffect` with `window.addEventListener('keydown', ...)`, guard `if (viewState !== 'preview') return`, cleanup on return
- `.course-preview-view` uses `display: flex; flex-direction: row` (not grid like home view)
- `.course-sidebar` in preview gets `flex: 0 0 220px` fixed width to match visual proportion
- `.panel-footer` uses `border-top: var(--border-pixel)` to visually separate Begin Study CTA
- `previewLoading` separate from global `isLoading` — fetch both lists in single `Promise.all`
- Textbooks list uses `aria-pressed={selectedTextbookId === tb.id}` for accessibility
- `npx tsc --noEmit` passes with zero errors after all edits
## Task 12 — CSS Pixel Art Study Desk Scene

### Technique Used
- **Layered divs** (Option B) inside `.scenery-placeholder` — far more maintainable than box-shadow pixel art.
- Fixed scene container: `320×400px` centered via existing flex layout in `.scenery-placeholder`.
- `image-rendering: pixelated` on `.scene-container` ensures crisp rendering.

### Stacking Context Pattern
- `.scene-window` gets `z-index: 1` to establish a stacking context — this scopes its children's z-indices and prevents star/moon z-indices from leaking to parent.
- `::before` / `::after` on `.scene-window` get `z-index: 1` within that context so dividers paint OVER stars.
- Remaining scene elements use z-index: 2 (desk), 3 (glow), 4 (lamp/books/mug).

### CSS Variables Confirmed Available
`--color-bg-primary`, `--color-bg-secondary`, `--color-bg-panel`, `--color-bg-panel-light`,
`--color-text-primary`, `--color-text-muted`, `--color-accent-primary`, `--color-accent-secondary`,
`--color-border`, `--color-border-bright`, `--border-pixel`, `--font-pixel`

### Animation
- Two separate `@keyframes` blocks: `scene-glow-pulse` (opacity 0.14→0.26 for the radial glow) and `scene-bulb-shimmer` (opacity 0.85→1 for the hot bulb point).
- CSS-only, 3s ease-in-out infinite. No JS.

### Gotchas
- `transparent` keyword is allowed (not a hex value). Used in `radial-gradient` fade-out and mug handle `background: transparent`.
- JSX indentation of closing `</div>` doesn't affect parse validity — TypeScript counts opens/closes syntactically, not by indentation.
- `radial-gradient(..., var(--color-accent-secondary), transparent 65%)` works correctly in modern CSS — CSS variables are valid inside gradient functions.
- Windowsill div (`scene-windowsill`) adds depth below the window frame for a more realistic wall+window look.

## Upload Progress Tracking Implementation

### Pattern: Polling-based Progress State Management
- Used `Record<string, {jobId, progress, step, error}>` to track multiple concurrent uploads
- Polling interval: 2 seconds with `setInterval` in `useEffect`
- Active jobs filtered by `progress < 100 && !error` to avoid polling completed/errored uploads
- On completion: delete from state and call `loadCourses()` to refresh textbook_count

### Key Implementation Details
1. **State Structure**: `uploadProgress[courseId]` stores job metadata
2. **Job Capture**: `importTextbook()` returns `ImportJob` with `job_id` - captured immediately after call
3. **Progress Display**: Linear gradient background fill from 0-100% using CSS variable colors
4. **Step Text**: Displayed below course-item-count in 6px pixel font
5. **Error State**: Red border added via `.upload-error` class when `status.status === 'error'`

### CSS Additions
- `.course-item-progress`: 6px font, accent-secondary color, block display
- `.course-item.upload-error`: Red border using accent-primary color
- Progress fill: `linear-gradient(to right, var(--color-accent-secondary) ${progress}%, var(--color-bg-panel) ${progress}%)`

### TypeScript Validation
- Zero errors on `npx tsc --noEmit`
- Type-safe state updates with proper Record typing
- Async/await error handling with try-catch

### Both Views Updated
- Home view course list (lines 238-266)
- Preview view course list (lines 372-400)
- Consistent className and style logic across both


## [Task 12] CSS Pixel Art Scene — Study Desk

### What was replaced
- Previous scene used `scene-star--1` (double-dash) class naming; new uses `scene-star-1` (single-dash)
- Old scene had ~15 absolutely-positioned divs within a fixed 320×400 container (position:absolute layout)
- New scene uses flex-column layout: `scene-window` (flex:0 0 60%) + `scene-desk` (flex:1)
- Old TSX was malformed: `scene-container` opened at 14-space indent but no matching close at 14 spaces; edit fixed this

### CSS Architecture
- `.scene-container`: `width:100%; height:100%; align-self:stretch; display:flex; flex-direction:column`
- `.scene-window`: `flex:0 0 60%` — flex sizing instead of absolute positioning
- `.scene-desk`: `flex:1; position:relative` — holds lamp/books as absolutely-positioned children
- Lamp extends above desk with `top:-44px` — paints over window area naturally (DOM order = later = on top)
- Glow uses `radial-gradient(ellipse, var(--color-accent-secondary), transparent)` + opacity + blur — no hardcoded rgba
- Books use `.scene-book` base + `.scene-book-2` modifier for position/color override (standard BEM-adjacent pattern)

### Gotchas
- `filter:blur()` on glow causes minor stacking context; `pointer-events:none` prevents interaction blocking
- `.scenery-placeholder` has `align-items:center` — added `align-self:stretch` to scene-container to fill full height
- Edit tool hashes for `</div>` lines can collide (same trimmed content) — use line number to disambiguate
- The old scene CSS section (lines 436-684) was fully replaced — no orphan classes left



## [2026-02-28] Task — BookshelfPage Test Rewrite (30 tests)

### Test Architecture
- `vi.mock('../api/courses')`, `vi.mock('../api/textbooks')`, `vi.mock('../api/universityMaterials')` at module level
- `beforeEach`: `vi.clearAllMocks()` then set all `mockResolvedValue` defaults
- `renderBookshelf()` helper: `render(<MemoryRouter><BookshelfPage /></MemoryRouter>)`
- Settings navigation test needs `<Routes>` with `/` + `/settings` routes to verify navigation

### Key RTL Patterns
- `await screen.findByTitle('MECH0089')` — waits for async course load, gets the `.course-item` div (has `title={course.name}`)
- `fireEvent.doubleClick(courseItem)` — bubbles up correctly from title-attributed div
- `within(document.querySelector('.pixel-dialog') as HTMLElement).getByRole('button', { name: 'Delete' })` — scopes query inside open dialog to avoid ambiguity with sidebar Delete button
- `getByRole('button', { name: /Textbook/i })` — matches emoji-prefixed button text `📚 Textbook`
- `getByRole('button', { name: 'Create' })` instead of `getByTestId('create-course-submit')` — PixelButton does NOT forward `data-testid` to DOM (no `...rest` spread in PixelButton)

### PixelButton data-testid Gotcha
- `PixelButton` interface does NOT accept `data-testid` and does NOT spread `...rest` onto `<button>`
- `data-testid` on `<PixelButton>` is silently dropped — NOT in DOM
- TypeScript allows `data-*` on custom JSX elements but component must forward it
- `data-testid` only works on native `<input>` elements (create-course-input, textbook-file-input, material-file-input)
- Workaround: use `getByRole('button', { name: 'Create' })` and `within(dialog).getByRole('button', { name: 'Delete' })`

### PixelDialog Behavior
- `if (!isOpen) return null` — dialog returns null when closed, nothing in DOM
- Title text is only in DOM when dialog is open → safe to use `getByText('New Course')` to verify dialog open state
- Multiple dialogs: all closed ones return null → only one Cancel button in DOM when one dialog open

### `act()` warning
- Test #3 (shows Loading...) triggers an act() warning because getCourses() resolves after render without being awaited
- Warning is benign — test passes correctly (assert on synchronous `isLoading=true` before promise resolves

### Final Result: 30/30 tests passing
