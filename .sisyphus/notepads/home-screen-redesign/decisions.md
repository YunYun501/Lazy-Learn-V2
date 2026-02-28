# Decisions — Home Screen Redesign

## [2026-02-28] Confirmed Design Decisions

### Data Model
- Math Library: Special reserved course, auto-created via `INSERT OR IGNORE` in `initialize()`, protected (403 on delete/rename)
- Course fields: `id TEXT PK, name TEXT UNIQUE NOT NULL, created_at TEXT` — NO additional fields for v1
- `university_materials` table: `id TEXT PK, course_id TEXT NOT NULL, title TEXT NOT NULL, file_type TEXT NOT NULL, filepath TEXT NOT NULL, created_at TEXT NOT NULL`
- Cascade delete order: disk files → chapters → textbooks → university_materials → course record (all within single async DB connection)

### Frontend Architecture
- HOME_VIEW ↔ COURSE_PREVIEW_VIEW: `useState<'home' | 'preview'>('home')` — NOT react-router routes
- Both views live at `/` path
- CSS Grid layout: `grid-template-columns: 1fr 2fr 1fr` with gap
- Scenery: ONE static CSS-only scene (study desk with lamp, night sky window) — NO JavaScript animation
- Reserve Space: empty PixelPanel with "Coming Soon" text — NO functionality

### UX Decisions
- Course creation: "+ New Course" button → PixelDialog with name input
- Upload: "Upload" button → PixelDialog choice (Textbook/University Material)
- Delete: Confirmation PixelDialog (NOT window.confirm) with course name + cascade warning
- Progress: Background fill on course list item (NOT separate progress bar)
- Search: Client-side `filter()` with `.toLowerCase().includes()`

### Scope
- University materials: Upload/store ONLY — no processing, no AI, no parsing
- Delete during active upload: Block with 409
- Math Library: Not deletable, not renameable (both blocked with 403)
