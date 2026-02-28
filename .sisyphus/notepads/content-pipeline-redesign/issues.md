# Content Pipeline Redesign — Issues & Gotchas

## [2026-02-28] Session Init — Metis Review Findings

### Critical Risks (must handle in tasks)
1. **MinerU page-range extraction untested** — `start_page_id`/`end_page_id` in `mineru_parser.py:50-51` have NEVER been called with non-default values. Task 1 spike MUST validate before any extraction work. If they don't work, propose alternative (extract whole book, split output by page).
2. **MinerU content type vocabulary unknown** — `mineru_parser.py:67` only checks `type == "discarded"`. All other types unknown. Spike must catalog them.
3. **Pipeline can't pause** — `process_pdf_background()` in `textbooks.py:44-79` is single uninterruptible background task. Must be fully replaced with multi-phase orchestrator.
4. **BookshelfPage.tsx at 655 lines** — 20+ useState hooks. Must extract `CoursePreviewView` (Task 12) BEFORE adding chapter verification UI (Task 14).

### High Risks
5. **Multiple MinerU calls performance** — Each call loads PDF fresh. Batch contiguous chapters into single call if possible.
6. **Manual SQLite migrations** — ALL new schema must be in single `_migrate_v2()` method called from `initialize()`. Test idempotency every time.
7. **Retroactive matching complexity** — Event-driven side effect triggered from material upload. Keep as direct function call (no event bus). Only trigger for textbooks in `toc_extracted` or later.

### Edge Cases (handle in relevant tasks)
- Single-chapter book: auto-select, skip verification UI
- Textbook with no TOC (AI fallback fails): proceed with single "Full Document" chapter
- Course materials uploaded before textbook: summaries stored, matching fires when textbook imported
- User closes browser during verification: pipeline state persists in DB (not lost)
- Partial MinerU failure: mark failed chapter as `error`, continue with others
- Re-importing same textbook: reject (error or ignore based on filename/hash)
- Chapter with 0-page range (page_start == page_end): handle gracefully
- University material with no extractable text: graceful error, not crash
- Concurrent imports: DB-based state prevents in-memory conflicts

### Code Patterns (FORBIDDEN)
- NO: `_job_status[textbook_id] = "processing"` → use `store.update_textbook_pipeline_status()`
- NO: `import alembic` or `from sqlalchemy` → manual SQL only
- NO: Vector/embedding imports — no semantic search in this plan
- NO: `import redux` or `import zustand` — useState only
