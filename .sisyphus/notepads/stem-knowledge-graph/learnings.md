# Learnings

## [2026-03-16] Session ses_30c06a8f9ffeAvmhTIrMncJj4K — Plan Start

### Architecture Conventions
- Backend: FastAPI + Python 3.11+, async throughout, aiosqlite (raw SQL, NO ORM)
- Frontend: React 19 + TypeScript + Vite, custom pixel-art UI (PixelButton, PixelPanel, PixelDialog)
- State: Custom React hooks, no Redux, direct fetch() calls
- API pattern: `API_BASE` from `api/config.ts`, fetch-based clients in `src/api/`
- All DB access via MetadataStore class — positional/keyword args (NOT dict payloads)
- MetadataStore key method sigs:
  - `create_course(name: str) -> str`
  - `create_textbook(title, filepath, course=None, library_type="course", textbook_id=None) -> str`
  - `assign_textbook_to_course(textbook_id, course_id)`
  - `update_textbook_pipeline_status(textbook_id, status)`
  - `create_chapter(textbook_id, chapter_number, title, page_start, page_end, description_path=None) -> str`
  - `update_chapter_extraction_status(chapter_id, status)`
- Migration pattern: idempotent in-code (V2 style with MIGRATE_V2_SQL + _migrate_v2() + try/except)
- AI calls MUST go through AIRouter — never direct API calls
- Long operations use FastAPI BackgroundTasks

### Package Naming (CRITICAL)
- MUST use `@xyflow/react` (NOT `reactflow` — old package)
- MUST use `@dagrejs/dagre` (NOT `dagre` — unmaintained)
- NEVER install ELK.js

### React Flow Rules
- MUST wrap page in `<ReactFlowProvider>`
- MUST set `onlyRenderVisibleElements={true}`
- MUST set `nodesConnectable={false}` (read-only)
- MUST define `nodeTypes` at MODULE LEVEL (not inside component)
- MUST wrap all custom node components in `React.memo()`
- MUST import `@xyflow/react/dist/style.css`
- MUST use React Flow `hidden` property for expand/collapse (NOT CSS display:none)
- Dagre config: `rankdir: 'TB'`, `nodesep: 80`, `ranksep: 120`

### Metis Insight
- Primary graph input: existing `ChapterDescription` data (key_concepts, prerequisites already extracted)
- Only call LLM for fine-grained relationship typing between concepts (~80% LLM cost savings vs raw extraction)

### Backend Test Commands
- ALWAYS `cd backend && python -m pytest tests/...` (not from root)
- Python scripts: `cd backend && python - <<'PY' ... PY`
- MetadataStore in tests: use `Path(tempfile.mkdtemp()) / 'test.db'` (NOT ':memory:')

## [2026-03-16] MetadataStore graph CRUD

### Backend Storage
- Graph CRUD tests live in `backend/tests/test_storage_graph.py`
- Graph CRUD methods added to `backend/app/services/storage.py` with positional args (no dict payloads)

## [2026-03-16] CRITICAL BUG: Subagents Write to Wrong Directory

### The Problem
Subagents repeatedly write files to `C:\Local\Github\Lazy_Learn\` (main branch) instead of `C:\Local\Github\Lazy_Learn_stem\` (feature worktree). This has happened for: T3, T5, T9, T11.

### Root Cause
Subagents default to the main repo when they don't explicitly use the full worktree path. They "confirm" file creation but haven't actually verified the absolute path.

### Mitigation for ALL Future Delegations
Every delegation prompt MUST include this exact verification step in MUST DO:
```
CRITICAL: Before writing any file, verify you are in the correct worktree:
1. Run `ls "C:/Local/Github/Lazy_Learn_stem/[directory]"` to confirm it exists
2. Use ABSOLUTE paths: `C:\Local\Github\Lazy_Learn_stem\...` (NOT relative paths)
3. After writing, verify: `ls "C:/Local/Github/Lazy_Learn_stem/[path/to/file]"`
4. If file not found in worktree, check main repo: `ls "C:/Local/Github/Lazy_Learn/[same/path]"`
```

### Verification Protocol (ORCHESTRATOR)
After EVERY delegation involving file creation:
1. Run `ls "C:/Local/Github/Lazy_Learn_stem/[expected/path]"` IMMEDIATELY
2. If not found, check main repo, read the content, and copy it to the worktree manually
3. Run `rm "C:/Local/Github/Lazy_Learn/[stray/path]"` to clean up main repo

### New MetadataStore CRUD Signatures (for T6, T8 reference)
```python
create_concept_node(textbook_id, title, node_type, level, description=None, source_chapter_id=None, source_section_id=None, source_page=None, metadata_json=None) -> str
get_concept_nodes(textbook_id, level=None) -> list[dict]
get_concept_node(node_id) -> dict | None
delete_concept_nodes(textbook_id) -> int
create_concept_edge(textbook_id, source_node_id, target_node_id, relationship_type, confidence=1.0, reasoning=None) -> str
get_concept_edges(textbook_id) -> list[dict]
delete_concept_edges(textbook_id) -> int
create_graph_job(textbook_id, total_chapters=0) -> str
get_graph_job(job_id) -> dict | None
update_graph_job(job_id, status=None, progress_pct=None, processed_chapters=None, error=None, completed_at=None) -> None
get_latest_graph_job(textbook_id) -> dict | None
```
