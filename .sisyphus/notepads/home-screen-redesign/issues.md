# Issues — Home Screen Redesign

## [2026-02-28] Known Gotchas

### Backend Gotchas
- `_job_status` dict lives in `textbooks.py` module scope — courses router must IMPORT it to check active uploads before allowing delete
- `CREATE_TABLES_SQL` is a single multiline string — new `university_materials` table must be appended to it
- `initialize()` creates all tables + must also run `ALTER TABLE textbooks ADD COLUMN course_id TEXT` after table creation
- `create_course()` at storage.py:163 uses `INSERT OR IGNORE` — Math Library auto-creation should follow same pattern
- `getTextbooks()` in textbooks.py filters by `course` TEXT (name), NOT by `course_id`. When fetching course textbooks in Course Preview, filter client-side by `course_id` or add a new backend query.

### Frontend Gotchas
- `textbooks.course` TEXT field is rendered in `BookshelfPage.tsx` as `.book-course-tag` — old component, will be deleted
- `importTextbook()` takes `(file, course?)` — adding `course_id` param is a 3rd optional argument
- `BookshelfPage.test.tsx` mocks at lines 9-13 — rewrite will delete old mocks too
- `window.confirm()` used for textbook deletion in old BookshelfPage — must be replaced with PixelDialog everywhere

### CSS Gotchas
- `bookshelf.css` is 368 lines — completely delete, do NOT try to adapt old styles
- All new CSS must use variables from `theme.css` — never hardcode hex colors or px values

## [2026-02-28] Task 3 - Courses Router

### Gotchas Found
- get_storage() uses MetadataStore() with no args (DEFAULT_DB_PATH) -- tests write to backend/data/lazy_learn.db during pytest run. Use unique names (uuid suffix) per test to avoid cross-test contamination.
- _job_status dict in textbooks.py: active upload check uses status_info.get('textbook_id') as inner key (not the outer job_id). Compare against course textbook IDs.
- Router POST /api/courses/ returns 200 (not 201) to match existing router conventions.
- update_course() in storage.py does NOT validate duplicate names -- router must check list_courses() before calling update_course().
