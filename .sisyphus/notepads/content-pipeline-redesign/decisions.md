# Content Pipeline Redesign — Decisions

## [2026-02-28] Session Init — All User Decisions

### Pipeline Scope
- **Pipeline only**: Content processing foundation only. Skills DB, question gen, tutoring, clickable derivations = future plans.
- **Foundation mindset**: Schema and storage must be designed for future extensibility (correct FKs, extensible types, clean APIs) but we don't build those features now.

### UX Decisions
- **User verification**: Inline on Course Preview panel (toggle chapters on/off). NOT a modal or separate page.
- **Chapter list**: Title + page range + relevance badge ONLY. No previews, no drag-and-drop, no inline descriptions.
- **Relevance badge**: High (>0.7), Medium (0.4-0.7), Low (<0.4). Pre-select chapters above 0.5.
- **Deferred extraction**: Manual button only. NO auto-background processing.

### Technical Decisions
- **Subchapter depth**: 2 levels only (chapter + section). Degrade gracefully if TOC has no level-2 entries.
- **Content persistence**: Generate once, store forever. No on-demand regeneration.
- **Textbook-first import**: Full TOC + basic processing even without materials. Skip relevance if no materials.
- **Retroactive matching**: Triggered when material uploaded to course that already has textbooks.
- **Pipeline state**: Persistent in DB (not in-memory). States: uploaded → toc_extracted → awaiting_verification → extracting → partially_extracted → fully_extracted → error
- **Chapter status**: pending → selected → extracting → extracted → deferred → error
- **DeepSeek budget**: No constraints (use freely)
- **Test strategy**: TDD (RED → GREEN → REFACTOR). Tests written BEFORE implementation.
- **Material summarization**: One DeepSeek call per material document (not per-slide).
- **Content storage**: DB records + separate files. DB for search/browsing. Files for raw access.

### Auto-Resolved Defaults
- Summary format: JSON in `summary_json TEXT` column with structured topics list
- Content type mapping: Deferred to spike results — schema uses generic `content_type TEXT`
- Polling interval: 2s (matching existing upload progress pattern)
