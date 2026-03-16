# STEM Knowledge Graph — GitNexus-like Concept Visualization

## TL;DR

> **Quick Summary**: Build an interactive knowledge graph that visualizes relationships between STEM concepts (theorems, proofs, derivations) extracted from textbook content, integrated into Lazy Learn's existing architecture.
> 
> **Deliverables**:
> - Backend: Knowledge graph builder service + SQLite schema + API endpoints
> - Frontend: React Flow graph page (`/graph/:textbookId`) with custom node types + concept details panel
> - LLM pipeline: Relationship extraction from existing ChapterDescription data + fine-grained edge typing
> - Multi-level expand/collapse: chapter → section → equation drill-down
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: Schema + Types → Graph Builder Service → API Endpoints → Graph Page + React Flow

---

## Context

### Original Request
Build a GitNexus-like app for studying STEM subjects. STEM subjects have inherent logical relationships (math proofs, logical reasoning) that can be presented as a graph. In the CoursePreviewView, a "Generate Relationship" button triggers graph generation, showing a full graph of relationships between ideas. Relationships include theorems, proofs, derivations, etc., generated primarily from MinerU-extracted content.

### Interview Summary
**Key Discussions**:
- **Visualization**: React Flow (@xyflow/react) chosen for native React integration, custom nodes, zoom/pan
- **Scope**: Per-textbook MVP — graph covers one textbook's concepts. Cross-textbook deferred.
- **Trigger**: On-demand — user clicks "Generate Relationship" button, graph builds in background
- **Storage**: Extend SQLite with new tables (no new DB dependencies)
- **Granularity**: Multi-level expandable — chapter overview → section detail → equation level
- **Display**: Dedicated new page `/graph/:textbookId` with its own route
- **Node interaction**: Click → concept details panel (definition, source, equations)
- **Relationship types**: derives_from, proves, prerequisite_of, uses, generalizes, specializes, contradicts, defines, equivalent_form
- **Tests**: TDD (pytest-asyncio backend, vitest frontend)

**Research Findings**:
- Existing `ChapterDescription` model already has `key_concepts` and `prerequisites` fields — this is the PRIMARY input for graph building (reduces LLM cost ~80% vs raw content extraction)
- MinerU `extracted_content` provides typed content (text/equation/table/figure) for equation-level nodes
- AIRouter already abstracts DeepSeek/OpenAI — graph prompts go through same channel
- CoursePreviewView has access to Course, Textbook[], PipelineStatus — all data needed for the button
- PixelButton/PixelDialog patterns exist for UI integration
- Pipeline BackgroundTasks pattern exists for async processing

### Metis Review
**Identified Gaps** (addressed):
- **Input source optimization**: Use ChapterDescription data (concepts, prerequisites already extracted) as primary input; only call LLM for fine-grained relationship typing between concepts. Saves ~80% LLM cost.
- **React Flow configuration**: Must use `ReactFlowProvider`, `onlyRenderVisibleElements`, memoized custom nodes, `@dagrejs/dagre` for layout
- **Package naming**: Must use `@xyflow/react` (not old `reactflow`), `@dagrejs/dagre` (not unmaintained `dagre`)
- **Expand/collapse pattern**: Use React Flow's `hidden` property on nodes (not CSS display:none)
- **Read-only graph**: Set `nodesConnectable={false}` — students view, not edit

---

## Work Objectives

### Core Objective
Enable students to visualize STEM concept relationships as an interactive, multi-level knowledge graph extracted from their textbooks.

### Concrete Deliverables
- `backend/app/services/knowledge_graph_builder.py` — LLM-powered relationship extraction service
- `backend/app/routers/knowledge_graph.py` — API endpoints for graph CRUD + generation
- `backend/app/models/knowledge_graph_models.py` — Pydantic models for graph data
- SQLite V3 migration — `concept_nodes` + `concept_edges` tables in `storage.py`
- `frontend/src/api/knowledgeGraph.ts` — API client
- `frontend/src/pages/GraphPage.tsx` — Dedicated graph exploration page
- `frontend/src/components/graph/` — React Flow graph viewer + custom node components + details panel
- `frontend/src/hooks/useKnowledgeGraph.ts` — Graph state management hook
- Route `/graph/:textbookId` registered in `App.tsx`
- "Generate Relationship" button in `CoursePreviewView.tsx`

### Definition of Done
- [ ] User clicks "Generate Relationship" on a textbook with extracted content → background job completes
- [ ] User navigates to `/graph/:textbookId` → sees interactive multi-level graph
- [ ] Clicking a chapter-level node expands to show section-level concepts
- [ ] Clicking a concept node shows details panel with definition + source reference
- [ ] Graph handles 50-200 nodes without performance degradation
- [ ] All relationship types rendered with distinct edge styles/labels
- [ ] All backend tests pass (`pytest`)
- [ ] All frontend tests pass (`vitest`)

### Must Have
- Multi-level expand/collapse (chapter → section → equation)
- 8 relationship types with visual distinction (derives_from, proves, prerequisite_of, uses, generalizes, specializes, contradicts, defines, equivalent_form)
- Concept details panel on node click
- Background generation with progress tracking
- Source traceability (each node links back to chapter/section/page)

### Must NOT Have (Guardrails)
- No cross-textbook graphs (MVP is per-textbook only)
- No graph editing by users (read-only visualization)
- No Neo4j or external graph database (SQLite only)
- No `reactflow` package (must use `@xyflow/react`)
- No `dagre` package (must use `@dagrejs/dagre`)
- No ELK.js (unnecessary complexity for MVP)
- No real-time collaborative features
- No export/sharing functionality
- No premature abstraction — keep services focused, no "generic graph framework"
- No over-commenting or JSDoc bloat on internal functions

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest-asyncio backend, vitest frontend)
- **Automated tests**: TDD (RED → GREEN → REFACTOR)
- **Framework**: pytest + pytest-asyncio (backend), vitest (frontend)
- **If TDD**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright — Navigate, interact, assert DOM, screenshot
- **API/Backend**: Use Bash (curl/httpie) — Send requests, assert status + response fields
- **Library/Module**: Use Bash (python REPL or pytest) — Import, call functions, compare output

### Playwright QA Environment Setup (MANDATORY for Tasks 12-18)
> Before ANY Playwright QA scenario can run, the executing agent MUST perform these setup steps.
> These are NOT optional — Playwright QA will fail without them.

```
SETUP PROCEDURE (run once before Playwright scenarios):
  1. Start backend: `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &`
     Wait for: `curl -s http://127.0.0.1:8000/docs` returns 200
  2. Start frontend: `cd frontend && bun run dev &`
     Wait for: `curl -s http://localhost:5173` returns 200
  3. Seed test data via API:
     a. Create course: `curl -X POST http://127.0.0.1:8000/api/courses -H 'Content-Type: application/json' -d '{"name":"QA Test Course"}'` → save course_id
     b. Import textbook: `curl -X POST http://127.0.0.1:8000/api/textbooks/import -F 'file=@backend/tests/fixtures/sample.pdf' -F 'course_id={course_id}'` → save textbook_id
     c. If no sample.pdf exists: create a minimal test fixture or use an existing textbook in the DB
     d. Trigger extraction: mark chapters as extracted via API or direct DB update
  4. For graph-specific scenarios:
     a. Trigger graph generation: `curl -X POST http://127.0.0.1:8000/api/knowledge-graph/{textbook_id}/build`
     b. Wait for completion: poll `/api/knowledge-graph/{textbook_id}/status` until status='completed'
  
TEARDOWN (after all Playwright scenarios):
  1. Kill backend: `pkill -f 'uvicorn app.main:app'`
  2. Kill frontend: `pkill -f 'bun run dev'`
  3. Clean test data: delete test course/textbook via API or reset DB
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — types, schema, config):
├── Task 1: SQLite V3 migration — concept_nodes + concept_edges tables [quick]
├── Task 2: Pydantic models for knowledge graph [quick]
├── Task 3: TypeScript types for graph data [quick]
├── Task 4: Install React Flow + dagre frontend dependencies [quick]
└── Task 5: Graph builder prompt templates [quick]

Wave 2 (Core services — backend + frontend skeleton):
├── Task 6: KnowledgeGraphBuilder service (depends: 1, 2, 5) [deep]
├── Task 7: MetadataStore graph CRUD methods (depends: 1, 2) [unspecified-high]
├── Task 8: Knowledge graph API router (depends: 2, 7) [unspecified-high]
├── Task 9: Frontend API client for knowledge graph (depends: 3) [quick]
├── Task 10: Custom React Flow node components (depends: 3, 4) [visual-engineering]
└── Task 11: Dagre layout utility (depends: 4) [quick]

Wave 3 (Integration — full pages + interactions):
├── Task 12: GraphPage with React Flow viewer (depends: 9, 10, 11) [visual-engineering]
├── Task 13: Concept details panel (depends: 10, 12) [visual-engineering]
├── Task 14: Multi-level expand/collapse logic (depends: 11, 12) [deep]
├── Task 15: "Generate Relationship" button + navigation (depends: 8, 9) [quick]
└── Task 16: Background job progress tracking (depends: 8, 15) [unspecified-high]

Wave 4 (Polish + Verification):
├── Task 17: Edge styling by relationship type (depends: 12) [visual-engineering]
├── Task 18: Graph page loading states + error handling (depends: 12, 16) [unspecified-high]
├── Task 19: Integration test — full pipeline (depends: all) [deep]

Wave FINAL (Independent review — 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real QA — full user flow (unspecified-high + playwright)
└── Task F4: Scope fidelity check (deep)

Critical Path: Task 1 → Task 7 → Task 8 → Task 15 → Task 16 → Task 19 → F1-F4
                Task 4 → Task 10 → Task 12 → Task 14 → Task 19
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 5 (Waves 1 & 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 6, 7 | 1 |
| 2 | — | 6, 7, 8 | 1 |
| 3 | — | 9, 10 | 1 |
| 4 | — | 10, 11 | 1 |
| 5 | — | 6 | 1 |
| 6 | 1, 2, 5 | 19 | 2 |
| 7 | 1, 2 | 8 | 2 |
| 8 | 2, 7 | 15, 16 | 2 |
| 9 | 3 | 12, 15 | 2 |
| 10 | 3, 4 | 12, 13 | 2 |
| 11 | 4 | 12, 14 | 2 |
| 12 | 9, 10, 11 | 13, 14, 17, 18 | 3 |
| 13 | 10, 12 | 19 | 3 |
| 14 | 11, 12 | 19 | 3 |
| 15 | 8, 9 | 16 | 3 |
| 16 | 8, 15 | 18, 19 | 3 |
| 17 | 12 | 19 | 4 |
| 18 | 12, 16 | 19 | 4 |
| 19 | all | F1-F4 | 4 |

### Agent Dispatch Summary

- **Wave 1**: **5** — T1-T5 → `quick`
- **Wave 2**: **6** — T6 → `deep`, T7 → `unspecified-high`, T8 → `unspecified-high`, T9 → `quick`, T10 → `visual-engineering`, T11 → `quick`
- **Wave 3**: **5** — T12 → `visual-engineering`, T13 → `visual-engineering`, T14 → `deep`, T15 → `quick`, T16 → `unspecified-high`
- **Wave 4**: **3** — T17 → `visual-engineering`, T18 → `unspecified-high`, T19 → `deep`
- **FINAL**: **4** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. SQLite V3 Migration — concept_nodes + concept_edges tables

  **What to do**:
  - Write RED tests first: test that `concept_nodes` and `concept_edges` tables exist after migration, test CRUD operations (insert/select/delete) on both tables
  - Add `MIGRATE_V3_SQL` constant to `backend/app/services/storage.py` following the V2 pattern
  - Create `concept_nodes` table: `id TEXT PRIMARY KEY`, `textbook_id TEXT NOT NULL` (FK to textbooks), `title TEXT NOT NULL`, `description TEXT`, `node_type TEXT NOT NULL` (theorem/definition/equation/lemma/concept/example), `level TEXT NOT NULL` (chapter/section/equation — for multi-level), `source_chapter_id TEXT` (FK to chapters), `source_section_id TEXT` (FK to sections), `source_page INTEGER`, `metadata_json TEXT` (flexible JSON for LaTeX, aliases, etc.), `created_at TEXT NOT NULL`
  - Create `concept_edges` table: `id TEXT PRIMARY KEY`, `textbook_id TEXT NOT NULL` (FK to textbooks), `source_node_id TEXT NOT NULL` (FK to concept_nodes), `target_node_id TEXT NOT NULL` (FK to concept_nodes), `relationship_type TEXT NOT NULL` (derives_from/proves/prerequisite_of/uses/generalizes/specializes/contradicts/defines/equivalent_form), `confidence REAL DEFAULT 1.0`, `reasoning TEXT`, `created_at TEXT NOT NULL`
  - Create index on `concept_nodes(textbook_id)` and `concept_edges(textbook_id)`
  - Create `graph_generation_jobs` table: `id TEXT PRIMARY KEY`, `textbook_id TEXT NOT NULL`, `status TEXT DEFAULT 'pending'` (pending/processing/completed/failed), `progress_pct REAL DEFAULT 0.0`, `total_chapters INTEGER DEFAULT 0`, `processed_chapters INTEGER DEFAULT 0`, `error TEXT`, `created_at TEXT NOT NULL`, `completed_at TEXT`
  - Add `_migrate_v3()` call inside `initialize()` method, following V2 pattern (idempotent, try/except)
  - GREEN: implement until all tests pass
  - REFACTOR: clean up

  **Must NOT do**:
  - Do NOT modify any existing V2 tables or columns
  - Do NOT add foreign key constraints that would break if parent tables are empty
  - Do NOT use any ORM — raw SQL only

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Schema addition following established V2 migration pattern — clear, bounded work
  - **Skills**: []
    - No specialized skills needed — follows existing pattern in storage.py
  - **Skills Evaluated but Omitted**:
    - `gitnexus/gitnexus-impact-analysis`: Not needed — adding new tables doesn't affect existing symbols

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5)
  - **Blocks**: Tasks 6, 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `backend/app/services/storage.py` lines containing `MIGRATE_V2_SQL` — Follow this exact migration pattern for V3
  - `backend/app/services/storage.py` `_migrate_v2()` method — Follow this idempotent try/except pattern
  - `backend/app/services/storage.py` `CREATE_TABLES_SQL` — Reference for table creation syntax used in this project

  **API/Type References**:
  - `backend/app/models/pipeline_models.py` `ExtractionStatus` enum — Reference for how status enums are defined

  **Test References**:
  - `backend/tests/` — Follow existing test file naming and structure patterns

  **WHY Each Reference Matters**:
  - `MIGRATE_V2_SQL`: The V3 migration MUST follow the identical pattern (idempotent ALTER TABLE with try/except) to avoid breaking existing databases
  - `_migrate_v2()`: Shows how to call migrations from `initialize()` — V3 must be called AFTER V2
  - `CREATE_TABLES_SQL`: Shows SQLite-specific syntax conventions (TEXT for dates, TEXT PRIMARY KEY, no auto-increment)

  **Acceptance Criteria**:

  - [ ] Test: `test_concept_nodes_table_exists` — insert a node, select it back, verify all fields
  - [ ] Test: `test_concept_edges_table_exists` — insert an edge, select it back, verify all fields
  - [ ] Test: `test_graph_generation_jobs_table_exists` — insert a job, select it back
  - [ ] Test: `test_v3_migration_idempotent` — call `initialize()` twice, no errors
  - [ ] `cd backend && python -m pytest tests/test_storage_v3.py -v` → PASS (4+ tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: V3 migration creates all tables on fresh database
    Tool: Bash (python)
    Preconditions: Delete test database if exists
    Steps:
      1. Run `cd backend && python -c "import asyncio, tempfile, os; from app.services.storage import MetadataStore; p=os.path.join(tempfile.mkdtemp(),'test.db'); ms=MetadataStore(p); asyncio.run(ms.initialize()); print('OK'); os.unlink(p)"`
      2. Assert output contains "OK" and no tracebacks
    Expected Result: All V3 tables created without error
    Failure Indicators: Any traceback, "table already exists" error (should be caught), or missing "OK"
    Evidence: .sisyphus/evidence/task-1-v3-migration-fresh.txt

  Scenario: V3 migration is idempotent on existing database
    Tool: Bash (python)
    Preconditions: Temp database file created
    Steps:
      1. Run `cd backend && python -c "import asyncio, tempfile, os; from app.services.storage import MetadataStore; p=os.path.join(tempfile.mkdtemp(),'test.db'); ms=MetadataStore(p); asyncio.run(ms.initialize()); asyncio.run(ms.initialize()); print('IDEMPOTENT_OK'); os.unlink(p)"`
      2. Assert output contains "IDEMPOTENT_OK" and no tracebacks
    Expected Result: Second initialize() completes without error
    Failure Indicators: Any "duplicate table" or "duplicate column" error
    Evidence: .sisyphus/evidence/task-1-v3-migration-idempotent.txt
  ```

  **Commit**: YES (groups with Task 2)
  - Message: `feat(knowledge-graph): add schema and models for concept nodes/edges`
  - Files: `backend/app/services/storage.py`, `backend/tests/test_storage_v3.py`
  - Pre-commit: `cd backend && python -m pytest tests/test_storage_v3.py -v`

- [x] 2. Pydantic Models for Knowledge Graph

  **What to do**:
  - Write RED tests first: test model validation (required fields, enum constraints, JSON serialization)
  - Create `backend/app/models/knowledge_graph_models.py`
  - Define enums: `NodeType(str, Enum)` — theorem, definition, equation, lemma, concept, example; `RelationshipType(str, Enum)` — derives_from, proves, prerequisite_of, uses, generalizes, specializes, contradicts, defines, equivalent_form; `GraphJobStatus(str, Enum)` — pending, processing, completed, failed; `NodeLevel(str, Enum)` — chapter, section, equation
  - Define models: `ConceptNode(BaseModel)` — id, textbook_id, title, description, node_type (NodeType), level (NodeLevel), source_chapter_id, source_section_id, source_page, metadata_json (Optional[dict]), created_at; `ConceptEdge(BaseModel)` — id, textbook_id, source_node_id, target_node_id, relationship_type (RelationshipType), confidence (float 0-1), reasoning, created_at
  - Define request/response models: `BuildGraphRequest` — textbook_id; `BuildGraphResponse` — job_id, status, message; `GraphStatusResponse` — job_id, textbook_id, status, progress_pct, total_chapters, processed_chapters, error; `GraphDataResponse` — textbook_id, nodes (list[ConceptNode]), edges (list[ConceptEdge])
  - GREEN: implement until tests pass
  - REFACTOR: ensure Pydantic v2 model_config patterns match existing models

  **Must NOT do**:
  - Do NOT put business logic in models — they are pure data containers
  - Do NOT import from services layer

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward Pydantic model definitions following existing patterns
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - None relevant — this is pure data model definition

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5)
  - **Blocks**: Tasks 6, 7, 8
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `backend/app/models/pipeline_models.py` — Follow this exact pattern for enum + BaseModel definitions
  - `backend/app/models/description_schema.py` `ConceptEntry` — Shows how concepts are currently modeled (name, aliases, classification)
  - `backend/app/models/ai_models.py` — Shows response model patterns

  **WHY Each Reference Matters**:
  - `pipeline_models.py`: Shows Pydantic v2 conventions used in this project (str Enum base, BaseModel fields, Optional typing)
  - `description_schema.py`: The `ConceptEntry` model has `name`, `aliases`, `classification` — graph nodes should be compatible with this existing concept representation
  - `ai_models.py`: Shows how to structure AI response models — relevant for graph extraction responses

  **Acceptance Criteria**:

  - [ ] Test: `test_node_type_enum_values` — all 6 node types exist
  - [ ] Test: `test_relationship_type_enum_values` — all 9 relationship types exist
  - [ ] Test: `test_concept_node_model_validation` — required fields enforced
  - [ ] Test: `test_graph_data_response_serialization` — JSON round-trip
  - [ ] `cd backend && python -m pytest tests/test_knowledge_graph_models.py -v` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Models serialize to valid JSON for API responses
    Tool: Bash (python)
    Preconditions: Models module importable from backend/
    Steps:
      1. Run `cd backend && python -c "from app.models.knowledge_graph_models import ConceptNode, GraphDataResponse; import json; n = ConceptNode(id='n1', textbook_id='tb1', title='Test', node_type='theorem', level='chapter', created_at='2026-01-01'); print(n.model_dump_json()); print('SERIALIZE_OK')"`
      2. Assert output contains "SERIALIZE_OK" and valid JSON
    Expected Result: All models produce valid JSON with correct field names
    Failure Indicators: ValidationError on construction, missing fields in JSON
    Evidence: .sisyphus/evidence/task-2-model-serialization.txt

  Scenario: Invalid relationship type rejected by validation
    Tool: Bash (python)
    Preconditions: Models module importable from backend/
    Steps:
      1. Run `cd backend && python -c "from app.models.knowledge_graph_models import ConceptEdge; try: ConceptEdge(id='e1', textbook_id='tb1', source_node_id='n1', target_node_id='n2', relationship_type='invalid_type', created_at='2026-01-01'); print('FAIL_NO_ERROR') except Exception as e: print(f'VALIDATION_OK: {type(e).__name__}')"`
      2. Assert output contains "VALIDATION_OK"
    Expected Result: Pydantic rejects invalid enum value
    Failure Indicators: Output shows "FAIL_NO_ERROR"
    Evidence: .sisyphus/evidence/task-2-model-validation-error.txt
  ```

  **Commit**: YES (groups with Task 1)
  - Message: `feat(knowledge-graph): add schema and models for concept nodes/edges`
  - Files: `backend/app/models/knowledge_graph_models.py`, `backend/tests/test_knowledge_graph_models.py`
  - Pre-commit: `cd backend && python -m pytest tests/test_knowledge_graph_models.py -v`

- [x] 3. TypeScript Types for Graph Data

  **What to do**:
  - Write RED tests first (vitest): test type guards and helper functions
  - Create `frontend/src/types/knowledgeGraph.ts`
  - Define types mirroring backend models: `NodeType` union type ('theorem' | 'definition' | 'equation' | 'lemma' | 'concept' | 'example'); `RelationshipType` union type (all 9 types); `NodeLevel` union type ('chapter' | 'section' | 'equation'); `GraphJobStatus` union type
  - Define interfaces: `ConceptNode` — id, textbookId, title, description, nodeType, level, sourceChapterId, sourceSectionId, sourcePage, metadata; `ConceptEdge` — id, textbookId, sourceNodeId, targetNodeId, relationshipType, confidence, reasoning; `GraphData` — textbookId, nodes, edges; `GraphJobStatus` — jobId, textbookId, status, progressPct, totalChapters, processedChapters, error
  - Define React Flow compatible types: `ConceptNodeData extends NodeProps` — concept data for custom node rendering; `ConceptEdgeData` — edge data for custom edge rendering
  - Add type guard functions: `isValidNodeType()`, `isValidRelationshipType()`
  - GREEN: implement until tests pass

  **Must NOT do**:
  - Do NOT use `any` type anywhere
  - Do NOT duplicate logic that belongs in components

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure TypeScript type definitions — bounded, straightforward
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4, 5)
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `frontend/src/types/pipeline.ts` — Follow this exact pattern for TypeScript type definitions in this project
  - `frontend/src/api/courses.ts` — Shows interface patterns with camelCase field names

  **External References**:
  - React Flow Node type: `import { Node, Edge, NodeProps } from '@xyflow/react'` — custom node data extends these

  **WHY Each Reference Matters**:
  - `pipeline.ts`: Shows how backend snake_case fields map to frontend camelCase in this codebase
  - React Flow types: Custom nodes MUST extend `NodeProps<T>` to receive data correctly

  **Acceptance Criteria**:

  - [ ] `npx tsc --noEmit` passes with 0 errors
  - [ ] Type guards return correct boolean for valid/invalid inputs
  - [ ] All 9 relationship types and 6 node types defined

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: TypeScript types compile without errors
    Tool: Bash
    Preconditions: Frontend dependencies installed
    Steps:
      1. Run `cd frontend && npx tsc --noEmit`
      2. Assert exit code 0
    Expected Result: Zero type errors
    Failure Indicators: Any "TS2xxx" error in output
    Evidence: .sisyphus/evidence/task-3-tsc-check.txt

  Scenario: Type guard rejects invalid relationship type
    Tool: Bash (vitest)
    Preconditions: Test file created
    Steps:
      1. Run `cd frontend && npx vitest run src/types/knowledgeGraph.test.ts`
      2. Assert all tests pass
    Expected Result: Type guards correctly validate inputs
    Failure Indicators: Test failures
    Evidence: .sisyphus/evidence/task-3-type-guards.txt
  ```

  **Commit**: YES (groups with Tasks 4, 5)
  - Message: `feat(knowledge-graph): add frontend types, dependencies, and prompt templates`
  - Files: `frontend/src/types/knowledgeGraph.ts`, `frontend/src/types/knowledgeGraph.test.ts`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

- [x] 4. Install React Flow + Dagre Frontend Dependencies

  **What to do**:
  - Run `cd frontend && bun add @xyflow/react @dagrejs/dagre`
  - Verify installation: import test in a scratch file
  - Verify `@xyflow/react` is in `package.json` dependencies (NOT `reactflow`)
  - Verify `@dagrejs/dagre` is in `package.json` dependencies (NOT `dagre`)
  - Create `frontend/src/styles/graph.css` with base React Flow style import and pixel-art theme overrides for graph nodes/edges (matching existing theme.css color palette: deep navy bg, hot pink accent, warm amber)

  **Must NOT do**:
  - Do NOT install `reactflow` (old package name)
  - Do NOT install `dagre` (unmaintained)
  - Do NOT install ELK.js
  - Do NOT modify existing CSS files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Package installation + minimal CSS file
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5)
  - **Blocks**: Tasks 10, 11
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `frontend/package.json` — Add dependencies here
  - `frontend/src/styles/theme.css` — Color palette variables to use in graph.css (--color-bg-deep, --color-accent-pink, --color-accent-amber, etc.)
  - `frontend/src/styles/pixel-components.css` — Pixel border and shadow patterns to apply to graph nodes

  **External References**:
  - `@xyflow/react` docs: `import '@xyflow/react/dist/style.css'` — MUST import base styles

  **WHY Each Reference Matters**:
  - `theme.css`: Graph nodes/edges MUST use existing color variables to maintain visual consistency with pixel-art design
  - `pixel-components.css`: Custom graph nodes should have pixel-art borders matching PixelPanel styling

  **Acceptance Criteria**:

  - [ ] `@xyflow/react` appears in package.json dependencies
  - [ ] `@dagrejs/dagre` appears in package.json dependencies
  - [ ] Neither `reactflow` nor `dagre` appear in package.json
  - [ ] `frontend/src/styles/graph.css` exists with base imports + theme overrides
  - [ ] `cd frontend && npx tsc --noEmit` passes

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: React Flow package installed correctly
    Tool: Bash
    Preconditions: Frontend directory exists
    Steps:
      1. Run `cd frontend && cat package.json | python -c "import sys,json; d=json.load(sys.stdin); print('@xyflow/react' in d.get('dependencies',{}))"`
      2. Assert output is "True"
      3. Run same check for `@dagrejs/dagre`
      4. Run same check to ensure `reactflow` is NOT present
    Expected Result: Correct packages installed, old packages absent
    Failure Indicators: "False" for @xyflow/react or @dagrejs/dagre, "True" for reactflow
    Evidence: .sisyphus/evidence/task-4-package-check.txt

  Scenario: React Flow base styles importable
    Tool: Bash
    Preconditions: Packages installed
    Steps:
      1. Run `cd frontend && npx tsc --noEmit`
      2. Assert no import errors for @xyflow/react
    Expected Result: TypeScript resolves all @xyflow/react imports
    Failure Indicators: "Cannot find module '@xyflow/react'" error
    Evidence: .sisyphus/evidence/task-4-import-check.txt
  ```

  **Commit**: YES (groups with Tasks 3, 5)
  - Message: `feat(knowledge-graph): add frontend types, dependencies, and prompt templates`
  - Files: `frontend/package.json`, `frontend/bun.lockb`, `frontend/src/styles/graph.css`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

- [x] 5. Graph Builder Prompt Templates

  **What to do**:
  - Write RED tests first: test prompt rendering with sample chapter description data
  - Create `backend/app/services/knowledge_graph_prompts.py`
  - Define `CONCEPT_EXTRACTION_PROMPT` — takes ChapterDescription data (key_concepts, prerequisites, mathematical_content) and produces structured JSON with concept nodes and their attributes (node_type, description, aliases)
  - Define `RELATIONSHIP_EXTRACTION_PROMPT` — takes a list of extracted concepts from multiple chapters and produces edges with relationship_type, source, target, confidence, reasoning
  - Define `EQUATION_LEVEL_PROMPT` — takes a section's extracted_content (equations, text) and produces fine-grained equation-level nodes and relationships
  - Each prompt must specify the exact JSON output schema including all 9 relationship types and 6 node types
  - Include few-shot examples in prompts for each STEM domain: math (theorems/proofs), physics (equations/derivations), engineering (circuits/equivalent forms)
  - Define `parse_concept_extraction_response(raw: str) -> list[dict]` and `parse_relationship_response(raw: str) -> list[dict]` — robust JSON parsing with fallback for malformed LLM output
  - GREEN: implement until tests pass

  **Must NOT do**:
  - Do NOT hardcode any API keys
  - Do NOT call the AI directly — prompts are templates consumed by the graph builder service
  - Do NOT use f-strings for prompt construction (use `.format()` or Template for clarity)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Prompt template definitions + JSON parsers — bounded scope
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4)
  - **Blocks**: Task 6
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `backend/app/models/description_schema.py` `ChapterDescription` — This is the PRIMARY input data shape. Fields: key_concepts (list[ConceptEntry]), prerequisites (list[str]), mathematical_content (bool), summary, chapter_title
  - `backend/app/models/description_schema.py` `ConceptEntry` — Has: name, aliases, classification (EXPLAINS/USES), description — these map directly to graph nodes
  - `backend/app/services/description_generator.py` — Shows existing prompt patterns used with AIRouter
  - `backend/app/services/ai_router.py` — Shows how prompts are sent to LLM (will be called by graph builder, not by prompts module)

  **WHY Each Reference Matters**:
  - `ChapterDescription`: This IS the input. Prompts must reference its exact field names to extract concepts
  - `ConceptEntry`: Already has concept metadata (name, aliases, classification) — the extraction prompt should EXTEND this, not reinvent it
  - `description_generator.py`: Shows prompt engineering style used in this project — follow same conventions

  **Acceptance Criteria**:

  - [ ] Test: `test_concept_extraction_prompt_renders` — prompt contains expected placeholders filled
  - [ ] Test: `test_relationship_prompt_includes_all_9_types` — all relationship types listed in prompt
  - [ ] Test: `test_parse_concept_response_valid_json` — parses well-formed JSON
  - [ ] Test: `test_parse_concept_response_malformed` — gracefully handles malformed LLM output
  - [ ] `cd backend && python -m pytest tests/test_knowledge_graph_prompts.py -v` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Prompt renders with real ChapterDescription data
    Tool: Bash (python)
    Preconditions: Prompt module importable from backend/
    Steps:
      1. Run `cd backend && python -c "from app.services.knowledge_graph_prompts import CONCEPT_EXTRACTION_PROMPT; result = CONCEPT_EXTRACTION_PROMPT.format(chapter_title='Maxwells Equations', key_concepts='Gausss Law: explains electromagnetic flux', prerequisites='Vector Calculus', mathematical_content='True'); assert 'Maxwells Equations' in result; assert 'Gausss Law' in result; print('RENDER_OK')"`
      2. Assert output contains "RENDER_OK"
    Expected Result: Prompt renders correctly with all data inserted
    Failure Indicators: KeyError on format, missing data in output
    Evidence: .sisyphus/evidence/task-5-prompt-render.txt

  Scenario: JSON parser handles malformed LLM output gracefully
    Tool: Bash (python)
    Preconditions: Parser functions importable from backend/
    Steps:
      1. Run `cd backend && python -c "from app.services.knowledge_graph_prompts import parse_concept_extraction_response; r1 = parse_concept_extraction_response('invalid json'); assert r1 == [], f'Expected empty list, got {r1}'; r2 = parse_concept_extraction_response('[{\"name\": \"test\"}]'); assert len(r2) == 1; print('PARSER_OK')"`
      2. Assert output contains "PARSER_OK"
    Expected Result: Graceful degradation on bad input, successful parse on good input
    Failure Indicators: Unhandled exception, assertion error
    Evidence: .sisyphus/evidence/task-5-parser-robustness.txt
  ```

  **Commit**: YES (groups with Tasks 3, 4)
  - Message: `feat(knowledge-graph): add frontend types, dependencies, and prompt templates`
  - Files: `backend/app/services/knowledge_graph_prompts.py`, `backend/tests/test_knowledge_graph_prompts.py`
  - Pre-commit: `cd backend && python -m pytest tests/test_knowledge_graph_prompts.py -v`

- [x] 6. KnowledgeGraphBuilder Service — Core Graph Generation

  **What to do**:
  - Write RED tests first: test graph building from mock ChapterDescription data, test LLM response parsing, test node/edge creation
  - Create `backend/app/services/knowledge_graph_builder.py`
  - Implement `KnowledgeGraphBuilder` class:
    - `__init__(self, store: MetadataStore, ai_router: AIRouter)` — inject dependencies
    - `async build_graph(self, textbook_id: str, job_id: str) -> None` — main orchestration method:
      1. Load all chapters for textbook from DB
      2. Load ChapterDescription data for each chapter (from `data/descriptions/{textbook_id}/chapter_{n}.md` or DB)
      3. **Phase 1 — Chapter-level nodes**: Create one node per chapter (level='chapter', node_type='concept')
      4. **Phase 2 — Section-level extraction**: For each chapter, use `CONCEPT_EXTRACTION_PROMPT` with ChapterDescription data → extract concepts as section-level nodes. Map `ConceptEntry.classification` (EXPLAINS/USES) to node_type. Link `prerequisites` as `prerequisite_of` edges.
      5. **Phase 3 — Relationship extraction**: Send all extracted concepts to `RELATIONSHIP_EXTRACTION_PROMPT` → get fine-grained edges (derives_from, proves, uses, etc.)
      6. **Phase 4 — Equation-level nodes** (optional, triggered by user later): Parse `extracted_content` where `content_type='equation'` → create equation-level nodes linked to their section
      7. Update job progress after each chapter: `processed_chapters += 1`, `progress_pct = processed/total`
      8. Store all nodes and edges via MetadataStore methods
      9. Mark job as 'completed' or 'failed' with error
    - `async _extract_concepts_from_description(self, chapter_desc: dict) -> list[dict]` — calls AIRouter with concept extraction prompt
    - `async _extract_relationships(self, concepts: list[dict]) -> list[dict]` — calls AIRouter with relationship prompt
    - `async _create_chapter_nodes(self, textbook_id: str, chapters: list) -> list[ConceptNode]` — create top-level chapter nodes
  - Handle errors gracefully: if LLM fails on one chapter, continue with others, log error
  - Use existing AIRouter pattern: `await ai_router.generate(prompt, model_preference='deepseek')` (check actual AIRouter API)
  - GREEN: implement until all tests pass
  - REFACTOR: extract helper methods, ensure error handling is consistent

  **Must NOT do**:
  - Do NOT call OpenAI/DeepSeek APIs directly — MUST go through AIRouter
  - Do NOT process all chapters in a single LLM call — process chapter by chapter for progress tracking
  - Do NOT block on LLM calls — use async/await throughout
  - Do NOT store duplicate nodes — check by title + textbook_id before inserting

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core business logic requiring LLM orchestration, multi-phase pipeline, error handling
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `gitnexus/gitnexus-exploring`: Not needed — references are explicit

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7, 8, 9, 10, 11)
  - **Blocks**: Task 19
  - **Blocked By**: Tasks 1, 2, 5

  **References**:

  **Pattern References**:
  - `backend/app/services/content_extractor.py` — Follow this async service pattern: class with store injection, async methods, background task orchestration
  - `backend/app/services/description_generator.py` — Shows how to call AIRouter with prompts and parse responses
  - `backend/app/services/pipeline_orchestrator.py` — Shows background job pattern with status tracking
  - `backend/app/services/ai_router.py` — The actual API for sending prompts. Check method signatures.

  **API/Type References**:
  - `backend/app/models/knowledge_graph_models.py` (Task 2) — ConceptNode, ConceptEdge models
  - `backend/app/models/description_schema.py` `ChapterDescription` — PRIMARY input data shape
  - `backend/app/services/knowledge_graph_prompts.py` (Task 5) — Prompt templates to use

  **WHY Each Reference Matters**:
  - `content_extractor.py`: This is the CLOSEST pattern — an async service that processes chapters in sequence, stores results, tracks progress
  - `description_generator.py`: Shows the EXACT way to call AIRouter and parse JSON responses
  - `pipeline_orchestrator.py`: Shows how background jobs update status — graph builder must follow same pattern
  - `ChapterDescription`: The key_concepts and prerequisites fields ARE the primary input — don't re-extract from raw text

  **Acceptance Criteria**:

  - [ ] Test: `test_build_graph_creates_chapter_nodes` — mock 3 chapters, verify 3 chapter-level nodes created
  - [ ] Test: `test_build_graph_extracts_concepts` — mock AIRouter response, verify section-level nodes created
  - [ ] Test: `test_build_graph_creates_edges` — mock relationship extraction, verify edges with correct types
  - [ ] Test: `test_build_graph_updates_progress` — verify job progress updates after each chapter
  - [ ] Test: `test_build_graph_handles_llm_failure` — mock AIRouter error, verify job continues with other chapters
  - [ ] `cd backend && python -m pytest tests/test_knowledge_graph_builder.py -v` → PASS (5+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Graph builder creates nodes from ChapterDescription data
    Tool: Bash (pytest)
    Preconditions: Mock AIRouter returns valid JSON concept list
    Steps:
      1. Create in-memory MetadataStore with test textbook + 2 chapters
      2. Create mock description files with key_concepts and prerequisites
      3. Call build_graph(textbook_id, job_id)
      4. Query concept_nodes table — assert nodes exist with correct types and levels
      5. Query concept_edges table — assert prerequisite edges created
    Expected Result: Nodes and edges stored in DB matching LLM output
    Failure Indicators: Empty tables, wrong node_type values, missing edges
    Evidence: .sisyphus/evidence/task-6-graph-builder-nodes.txt

  Scenario: Graph builder handles LLM failure gracefully
    Tool: Bash (pytest)
    Preconditions: Mock AIRouter raises exception on chapter 2 of 3
    Steps:
      1. Call build_graph with 3 chapters, AIRouter fails on chapter 2
      2. Assert chapters 1 and 3 have nodes
      3. Assert job status is 'completed' (not 'failed') with partial results
      4. Assert error is logged
    Expected Result: Partial graph built, no crash, error recorded
    Failure Indicators: Unhandled exception, job status 'failed', no nodes for any chapter
    Evidence: .sisyphus/evidence/task-6-graph-builder-error.txt
  ```

  **Commit**: YES (groups with Task 7)
  - Message: `feat(knowledge-graph): implement graph builder service and DB methods`
  - Files: `backend/app/services/knowledge_graph_builder.py`, `backend/tests/test_knowledge_graph_builder.py`
  - Pre-commit: `cd backend && python -m pytest tests/test_knowledge_graph_builder.py -v`

- [x] 7. MetadataStore Graph CRUD Methods

  **What to do**:
  - Write RED tests first: test each CRUD method with in-memory SQLite
  - Add methods to `backend/app/services/storage.py` `MetadataStore` class:
    - `async create_concept_node(self, data: dict) -> str` — insert node, return id
    - `async get_concept_nodes(self, textbook_id: str, level: Optional[str] = None) -> list[dict]` — get all nodes for textbook, optionally filtered by level
    - `async get_concept_node(self, node_id: str) -> Optional[dict]` — get single node
    - `async delete_concept_nodes(self, textbook_id: str) -> int` — delete all nodes for textbook (for regeneration)
    - `async create_concept_edge(self, data: dict) -> str` — insert edge, return id
    - `async get_concept_edges(self, textbook_id: str) -> list[dict]` — get all edges for textbook
    - `async delete_concept_edges(self, textbook_id: str) -> int` — delete all edges for textbook
    - `async create_graph_job(self, data: dict) -> str` — create generation job
    - `async get_graph_job(self, job_id: str) -> Optional[dict]` — get job status
    - `async update_graph_job(self, job_id: str, updates: dict) -> None` — update progress/status
    - `async get_latest_graph_job(self, textbook_id: str) -> Optional[dict]` — get most recent job for textbook
  - Follow existing MetadataStore patterns: parameterized queries, row factory, async context managers
  - GREEN: implement until tests pass

  **Must NOT do**:
  - Do NOT use ORM — raw SQL with parameterized queries only
  - Do NOT modify existing methods
  - Do NOT add transaction management beyond what SQLite provides

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Many CRUD methods, but follows established patterns — medium complexity
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 8, 9, 10, 11)
  - **Blocks**: Task 8
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `backend/app/services/storage.py` `create_textbook()`, `list_textbooks()`, `get_textbook()` — Follow these EXACT patterns for CRUD methods
  - `backend/app/services/storage.py` `save_relevance_results()`, `get_relevance_results()` — Shows batch insert/query pattern
  - `backend/app/services/storage.py` row factory setup — Shows how dicts are returned from queries

  **WHY Each Reference Matters**:
  - Existing CRUD methods show the exact async pattern: `async with aiosqlite.connect()`, `cursor.execute()`, `row_factory`, return dict — new methods MUST be identical in structure

  **Acceptance Criteria**:

  - [ ] Test: `test_create_and_get_concept_node` — insert + retrieve
  - [ ] Test: `test_get_nodes_filtered_by_level` — filter by chapter/section/equation
  - [ ] Test: `test_delete_nodes_by_textbook` — delete all, verify count
  - [ ] Test: `test_create_and_get_edges` — insert edges + retrieve by textbook
  - [ ] Test: `test_graph_job_lifecycle` — create → update progress → complete
  - [ ] `cd backend && python -m pytest tests/test_storage_graph.py -v` → PASS (5+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full CRUD lifecycle for concept nodes
    Tool: Bash (pytest)
    Preconditions: In-memory database initialized
    Steps:
      1. Create 3 concept nodes for textbook "tb-1"
      2. Get all nodes for "tb-1" — assert count is 3
      3. Get nodes filtered by level='chapter' — assert correct subset
      4. Delete all nodes for "tb-1" — assert returns 3
      5. Get all nodes for "tb-1" — assert count is 0
    Expected Result: All CRUD operations work correctly
    Failure Indicators: Wrong counts, missing data, SQL errors
    Evidence: .sisyphus/evidence/task-7-crud-lifecycle.txt

  Scenario: Graph job progress tracking
    Tool: Bash (pytest)
    Preconditions: In-memory database initialized
    Steps:
      1. Create job with status='pending', total_chapters=5
      2. Update: processed_chapters=2, progress_pct=0.4, status='processing'
      3. Get job — assert all fields match
      4. Update: status='completed', progress_pct=1.0
      5. Get latest job for textbook — assert returns this job
    Expected Result: Job lifecycle tracked accurately
    Failure Indicators: Status not updating, progress not persisted
    Evidence: .sisyphus/evidence/task-7-job-tracking.txt
  ```

  **Commit**: YES (groups with Task 6)
  - Message: `feat(knowledge-graph): implement graph builder service and DB methods`
  - Files: `backend/app/services/storage.py`, `backend/tests/test_storage_graph.py`
  - Pre-commit: `cd backend && python -m pytest tests/test_storage_graph.py -v`

- [x] 8. Knowledge Graph API Router

  **What to do**:
  - Write RED tests first: test each endpoint with TestClient
  - Create `backend/app/routers/knowledge_graph.py`
  - Implement endpoints:
    - `POST /api/knowledge-graph/{textbook_id}/build` — trigger graph generation as background task, return BuildGraphResponse with job_id. Check textbook exists and has extracted content. If graph already exists, delete old nodes/edges first (regenerate).
    - `GET /api/knowledge-graph/{textbook_id}/status` — return GraphStatusResponse with latest job progress
    - `GET /api/knowledge-graph/{textbook_id}/graph` — return GraphDataResponse with all nodes and edges
    - `GET /api/knowledge-graph/{textbook_id}/node/{node_id}` — return single ConceptNode with its connected edges
    - `DELETE /api/knowledge-graph/{textbook_id}` — delete all graph data for textbook
  - Register router in `backend/app/main.py`: `app.include_router(knowledge_graph.router)`
  - Use `BackgroundTasks` for the build endpoint (following existing textbooks.py pattern)
  - GREEN: implement until tests pass

  **Must NOT do**:
  - Do NOT put business logic in the router — delegate to KnowledgeGraphBuilder service
  - Do NOT allow graph generation on textbooks without extracted content (return 400)
  - Do NOT expose internal error details in API responses

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple endpoints with validation, background tasks, error handling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 9, 10, 11)
  - **Blocks**: Tasks 15, 16
  - **Blocked By**: Tasks 2, 7

  **References**:

  **Pattern References**:
  - `backend/app/routers/textbooks.py` — Follow this exact router pattern: router definition, BackgroundTasks usage, status tracking, error handling
  - `backend/app/main.py` — Where to register the new router (add `app.include_router()`)
  - `backend/app/routers/textbooks.py` `import_textbook()` — Background task trigger pattern to copy

  **API/Type References**:
  - `backend/app/models/knowledge_graph_models.py` (Task 2) — Request/response models

  **WHY Each Reference Matters**:
  - `textbooks.py`: The import_textbook endpoint is the CLOSEST analogue — triggers a background job, returns job_id, has a separate status endpoint. Copy this pattern exactly.
  - `main.py`: Router registration uses `app.include_router(router_module.router)` — follow same line pattern

  **Acceptance Criteria**:

  - [ ] Test: `test_build_endpoint_returns_job_id` — POST returns 202 with job_id
  - [ ] Test: `test_build_endpoint_rejects_no_content` — returns 400 for textbook without extracted content
  - [ ] Test: `test_status_endpoint` — returns job progress
  - [ ] Test: `test_graph_endpoint_returns_nodes_edges` — returns graph data
  - [ ] Test: `test_node_detail_endpoint` — returns single node with connections
  - [ ] Router registered in main.py
  - [ ] `cd backend && python -m pytest tests/test_knowledge_graph_router.py -v` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Build endpoint triggers background job
    Tool: Bash (curl)
    Preconditions: Backend running, textbook with extracted content exists
    Steps:
      1. curl -X POST http://127.0.0.1:8000/api/knowledge-graph/{textbookId}/build
      2. Assert response status 202
      3. Assert response JSON has "job_id" and "status" = "pending"
      4. curl http://127.0.0.1:8000/api/knowledge-graph/{textbookId}/status
      5. Assert response shows job in progress or completed
    Expected Result: Job created and trackable
    Failure Indicators: 404 (router not registered), 500 (service error), missing job_id
    Evidence: .sisyphus/evidence/task-8-build-endpoint.txt

  Scenario: Build endpoint rejects textbook without content
    Tool: Bash (curl)
    Preconditions: Backend running, textbook exists but has NO extracted chapters
    Steps:
      1. curl -X POST http://127.0.0.1:8000/api/knowledge-graph/{emptyTextbookId}/build
      2. Assert response status 400
      3. Assert error message mentions "extracted content"
    Expected Result: Clear 400 error preventing graph generation on empty textbook
    Failure Indicators: 200/202 (should reject), 500 (unhandled error)
    Evidence: .sisyphus/evidence/task-8-build-rejects-empty.txt
  ```

  **Commit**: YES (groups with Task 9)
  - Message: `feat(knowledge-graph): add API router and frontend client`
  - Files: `backend/app/routers/knowledge_graph.py`, `backend/app/main.py`, `backend/tests/test_knowledge_graph_router.py`
  - Pre-commit: `cd backend && python -m pytest tests/test_knowledge_graph_router.py -v`

- [x] 9. Frontend API Client for Knowledge Graph

  **What to do**:
  - Create `frontend/src/api/knowledgeGraph.ts`
  - Implement functions following existing API client patterns:
    - `buildGraph(textbookId: string): Promise<BuildGraphResponse>` — POST to `/api/knowledge-graph/{textbookId}/build`
    - `getGraphStatus(textbookId: string): Promise<GraphStatusResponse>` — GET status
    - `getGraphData(textbookId: string): Promise<GraphData>` — GET full graph
    - `getNodeDetail(textbookId: string, nodeId: string): Promise<ConceptNodeDetail>` — GET single node with edges
    - `deleteGraph(textbookId: string): Promise<void>` — DELETE graph
    - `pollGraphStatus(textbookId: string, intervalMs: number, onProgress: (status: GraphStatusResponse) => void): Promise<GraphStatusResponse>` — poll status endpoint until completed/failed
  - Use `API_BASE` from `api/config.ts` for all URLs
  - Handle response errors consistently (check `res.ok`, throw descriptive errors)
  - Apply snake_case → camelCase field transformation in responses

  **Must NOT do**:
  - Do NOT use axios or any HTTP library — use native `fetch()` matching existing pattern
  - Do NOT duplicate type definitions — import from `types/knowledgeGraph.ts`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: API client following established fetch-based pattern — bounded, clear
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8, 10, 11)
  - **Blocks**: Tasks 12, 15
  - **Blocked By**: Task 3

  **References**:

  **Pattern References**:
  - `frontend/src/api/textbooks.ts` — Follow this EXACT pattern for API client functions (fetch, error handling, return typing)
  - `frontend/src/api/config.ts` — Import `API_BASE` from here
  - `frontend/src/api/courses.ts` — Shows the interface export + fetch pattern

  **WHY Each Reference Matters**:
  - `textbooks.ts`: Every API client function in this project follows the same structure: construct URL with `API_BASE`, call `fetch()`, check `res.ok`, throw on error, return `res.json()`. New functions MUST be identical in style.

  **Acceptance Criteria**:

  - [ ] All 6 functions exported and typed
  - [ ] `API_BASE` imported from config.ts
  - [ ] `npx tsc --noEmit` passes
  - [ ] Response types match backend models

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: API client compiles and exports all functions
    Tool: Bash
    Preconditions: Frontend dependencies installed
    Steps:
      1. Run `cd frontend && npx tsc --noEmit`
      2. Assert 0 errors
    Expected Result: All API functions type-check correctly
    Failure Indicators: Any TS errors in knowledgeGraph.ts
    Evidence: .sisyphus/evidence/task-9-api-client-tsc.txt

  Scenario: pollGraphStatus stops on completion
    Tool: Bash (vitest)
    Preconditions: Test with mocked fetch
    Steps:
      1. Mock fetch to return status='processing' twice, then 'completed'
      2. Call pollGraphStatus with 100ms interval
      3. Assert onProgress called 3 times
      4. Assert final result has status='completed'
    Expected Result: Polling stops when status is terminal
    Failure Indicators: Infinite loop, missing callbacks
    Evidence: .sisyphus/evidence/task-9-polling-test.txt
  ```

  **Commit**: YES (groups with Task 8)
  - Message: `feat(knowledge-graph): add API router and frontend client`
  - Files: `frontend/src/api/knowledgeGraph.ts`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

- [x] 10. Custom React Flow Node Components

  **What to do**:
  - Write RED vitest tests first: test node rendering, test props handling
  - Create `frontend/src/components/graph/` directory
  - Create `ChapterNode.tsx` — chapter-level node component:
    - Pixel-art styled container (use PixelPanel pattern)
    - Display: chapter title, chapter number, concept count badge
    - Expand/collapse indicator (▶/▼)
    - Color: use `--color-accent-amber` from theme.css
    - `<Handle type="target" position={Position.Top} />` + `<Handle type="source" position={Position.Bottom} />`
  - Create `ConceptNode.tsx` — section-level concept node:
    - Display: concept name, node_type badge (theorem/definition/equation/etc.)
    - Color-coded by node_type: theorem=`--color-accent-pink`, definition=`--color-accent-amber`, equation=`--color-text-accent`
    - Click handler to select node (triggers details panel)
    - Handles for top + bottom connections
  - Create `EquationNode.tsx` — equation-level node:
    - Display: LaTeX equation rendered with KaTeX (already in project dependencies)
    - Smaller node size
    - Source page reference
  - Create `nodeTypes.ts` — export `const nodeTypes = { chapter: ChapterNode, concept: ConceptNode, equation: EquationNode }` (OUTSIDE any component, as a module-level constant)
  - All node components MUST be wrapped in `React.memo()` for performance
  - Apply pixel-art borders from `pixel-components.css` pattern

  **Must NOT do**:
  - Do NOT define nodeTypes inside a React component (causes re-registration on every render)
  - Do NOT use inline styles — use CSS classes from graph.css
  - Do NOT forget Handle components (edges won't connect without them)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Custom UI components with specific visual design requirements (pixel-art, color-coding, KaTeX)
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Needed for pixel-art visual consistency and node layout design

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8, 9, 11)
  - **Blocks**: Tasks 12, 13
  - **Blocked By**: Tasks 3, 4

  **References**:

  **Pattern References**:
  - `frontend/src/components/pixel/PixelPanel.tsx` — Follow this pattern for node container styling (pixel borders, variants)
  - `frontend/src/components/pixel/PixelBadge.tsx` — Use for node_type badge display
  - `frontend/src/styles/theme.css` — Color variables for node type color-coding
  - `frontend/src/styles/pixel-components.css` — Pixel border and shadow patterns

  **External References**:
  - React Flow custom nodes: `import { Handle, Position, NodeProps } from '@xyflow/react'`
  - KaTeX: `import 'katex/dist/katex.min.css'` + `import { InlineMath } from 'react-katex'` (already in project)

  **WHY Each Reference Matters**:
  - `PixelPanel.tsx`: Nodes must look like they belong in the pixel-art design system — same borders, shadows, fonts
  - `theme.css`: Color variables ensure visual consistency across the entire app
  - KaTeX: Already used in ContentRenderer — equation nodes should use same rendering approach

  **Acceptance Criteria**:

  - [ ] 3 node components: ChapterNode, ConceptNode, EquationNode
  - [ ] All wrapped in React.memo()
  - [ ] nodeTypes object defined at module level (not inside component)
  - [ ] Each node has top + bottom Handle components
  - [ ] Color-coded by node_type
  - [ ] `npx tsc --noEmit` passes
  - [ ] `npx vitest run src/components/graph/` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Node components render with correct content
    Tool: Bash (vitest)
    Preconditions: Test file with React Testing Library
    Steps:
      1. Render ChapterNode with data={title: "Ch 1: Limits", conceptCount: 5}
      2. Assert "Ch 1: Limits" is visible
      3. Assert expand indicator visible
      4. Render ConceptNode with data={title: "L'Hôpital's Rule", nodeType: "theorem"}
      5. Assert "theorem" badge is visible
    Expected Result: All nodes render their data correctly
    Failure Indicators: Missing text, wrong badge, render error
    Evidence: .sisyphus/evidence/task-10-node-render.txt

  Scenario: nodeTypes object is module-level constant
    Tool: Bash (vitest)
    Preconditions: nodeTypes.ts exists
    Steps:
      1. Import nodeTypes from the module
      2. Assert it has keys: 'chapter', 'concept', 'equation'
      3. Assert each value is a React component (typeof === 'object' with $$typeof)
    Expected Result: nodeTypes is a stable reference that won't cause re-renders
    Failure Indicators: nodeTypes defined inside component, missing keys
    Evidence: .sisyphus/evidence/task-10-nodetypes-stable.txt
  ```

  **Commit**: YES (groups with Task 11)
  - Message: `feat(knowledge-graph): create custom node components and layout utility`
  - Files: `frontend/src/components/graph/ChapterNode.tsx`, `ConceptNode.tsx`, `EquationNode.tsx`, `nodeTypes.ts`
  - Pre-commit: `cd frontend && npx vitest run`

- [x] 11. Dagre Layout Utility

  **What to do**:
  - Write RED vitest tests first: test layout computation with mock nodes/edges
  - Create `frontend/src/hooks/useGraphLayout.ts`
  - Implement `useGraphLayout(nodes: Node[], edges: Edge[]): { layoutNodes: Node[], layoutEdges: Edge[] }`:
    - Use `@dagrejs/dagre` to compute node positions
    - dagre config: `rankdir: 'TB'` (top-to-bottom), `nodesep: 80`, `ranksep: 120`
    - Set node dimensions based on type: chapter=200x80, concept=180x60, equation=160x50
    - Return new node array with computed `position: { x, y }` values
    - Wrap computation in `useMemo` depending on `[nodes, edges]` to prevent recalculation
  - Export `computeLayout(nodes, edges)` as a pure function (for testing without hooks)
  - GREEN: implement until tests pass

  **Must NOT do**:
  - Do NOT use ELK.js
  - Do NOT recalculate layout on every render — useMemo is mandatory
  - Do NOT mutate input arrays — return new arrays

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single utility hook + pure function — bounded scope
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8, 9, 10)
  - **Blocks**: Tasks 12, 14
  - **Blocked By**: Task 4

  **References**:

  **Pattern References**:
  - `frontend/src/hooks/usePanelLayout.ts` — Follow this hook pattern (useMemo, return object)

  **External References**:
  - dagre API: `import dagre from '@dagrejs/dagre'` → `new dagre.graphlib.Graph()`, `.setDefaultEdgeLabel()`, `.setNode()`, `.setEdge()`, `dagre.layout(g)`

  **WHY Each Reference Matters**:
  - `usePanelLayout.ts`: Shows how custom hooks are structured in this project — follow same export pattern
  - dagre API: The graph must be constructed with `setNode(id, { width, height })`, then `layout(g)` computes positions

  **Acceptance Criteria**:

  - [ ] `computeLayout()` pure function returns nodes with x/y positions
  - [ ] `useGraphLayout()` hook memoizes computation
  - [ ] dagre config uses TB direction, 80px node sep, 120px rank sep
  - [ ] `npx vitest run src/hooks/useGraphLayout.test.ts` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Layout computes valid positions for a simple graph
    Tool: Bash (vitest)
    Preconditions: Test file with mock nodes and edges
    Steps:
      1. Create 3 nodes (A → B → C chain)
      2. Call computeLayout(nodes, edges)
      3. Assert all returned nodes have position.x and position.y (numbers, not NaN)
      4. Assert node A is above node B (A.y < B.y in TB layout)
      5. Assert node B is above node C
    Expected Result: Hierarchical top-to-bottom layout computed
    Failure Indicators: NaN positions, wrong vertical order, same positions for all
    Evidence: .sisyphus/evidence/task-11-layout-compute.txt

  Scenario: Layout handles empty graph gracefully
    Tool: Bash (vitest)
    Preconditions: Test file
    Steps:
      1. Call computeLayout([], [])
      2. Assert returns empty arrays (no crash)
    Expected Result: Empty arrays returned, no error
    Failure Indicators: Exception thrown, undefined returned
    Evidence: .sisyphus/evidence/task-11-layout-empty.txt
  ```

  **Commit**: YES (groups with Task 10)
  - Message: `feat(knowledge-graph): create custom node components and layout utility`
  - Files: `frontend/src/hooks/useGraphLayout.ts`, `frontend/src/hooks/useGraphLayout.test.ts`
  - Pre-commit: `cd frontend && npx vitest run`

- [x] 12. GraphPage — Main Graph Exploration Page with React Flow

  **What to do**:
  - Write RED vitest tests first: test page renders, test React Flow container present
  - Create `frontend/src/pages/GraphPage.tsx`
  - Register route in `frontend/src/App.tsx`: `<Route path="/graph/:textbookId" element={<GraphPage />} />`
  - Implement GraphPage:
    - Extract `textbookId` from route params via `useParams()`
    - Fetch graph data on mount: call `getGraphData(textbookId)` from API client
    - Loading state: show pixel-art loading indicator while fetching
    - Error state: show error message if graph doesn't exist (with link to generate)
    - Render `<ReactFlowProvider>` wrapping the entire page
    - Render `<ReactFlow>` with: `nodes`, `edges`, `nodeTypes` (from Task 10), `onlyRenderVisibleElements={true}`, `nodesConnectable={false}`, `fitView`, `minZoom={0.1}`, `maxZoom={2}`
    - Import `@xyflow/react/dist/style.css` and `styles/graph.css`
    - Add `<MiniMap />`, `<Controls />`, `<Background />` from @xyflow/react
    - Add back button (PixelButton, variant="secondary") to navigate back to bookshelf
    - Add textbook title in header
    - Use `useGraphLayout()` hook to compute node positions from raw data
  - Create `frontend/src/hooks/useKnowledgeGraph.ts`:
    - Custom hook that manages graph page state: loading, error, graphData, selectedNodeId
    - Fetches data, transforms backend response to React Flow nodes/edges format
    - Maps `ConceptNode` → React Flow `Node<ConceptNodeData>` with `type` field matching nodeTypes keys

  **Must NOT do**:
  - Do NOT set `nodesConnectable={true}` — graph is read-only
  - Do NOT forget `<ReactFlowProvider>` wrapper
  - Do NOT forget to import `@xyflow/react/dist/style.css`
  - Do NOT define nodeTypes inside the component

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Full page composition with React Flow, layout, visual design matching pixel-art system
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Page composition, loading/error states, visual consistency

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14, 15, 16)
  - **Blocks**: Tasks 13, 14, 17, 18
  - **Blocked By**: Tasks 9, 10, 11

  **References**:

  **Pattern References**:
  - `frontend/src/pages/DeskPage.tsx` — Follow this page structure: useParams, useEffect for data loading, loading/error states
  - `frontend/src/App.tsx` — Where to add the new route
  - `frontend/src/components/pixel/` — PixelButton, PixelPanel for UI elements on the page

  **External References**:
  - React Flow: `import { ReactFlow, ReactFlowProvider, MiniMap, Controls, Background } from '@xyflow/react'`
  - React Flow styles: `import '@xyflow/react/dist/style.css'`

  **WHY Each Reference Matters**:
  - `DeskPage.tsx`: Closest existing page pattern — route params extraction, data loading on mount, multi-component layout
  - `App.tsx`: Route registration follows `<Route path="/..." element={<Page />} />` pattern

  **Acceptance Criteria**:

  - [ ] Route `/graph/:textbookId` registered in App.tsx
  - [ ] ReactFlowProvider wraps the page
  - [ ] ReactFlow renders with onlyRenderVisibleElements, nodesConnectable=false
  - [ ] MiniMap, Controls, Background rendered
  - [ ] Loading and error states handled
  - [ ] Back button navigates to bookshelf
  - [ ] `npx vitest run src/pages/GraphPage.test.tsx` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Graph page renders with node data
    Tool: Playwright
    Preconditions: Run "Playwright QA Environment Setup" from Verification Strategy section. Ensure step 4 (graph generation) is complete. Record the textbook_id used.
    Steps:
      1. Navigate to http://localhost:5173/graph/{textbookId}
      2. Wait for loading indicator to disappear (timeout: 10s)
      3. Assert `.react-flow` container is visible
      4. Assert at least 1 node element visible (selector: `.react-flow__node`)
      5. Assert MiniMap visible (selector: `.react-flow__minimap`)
      6. Take screenshot
    Expected Result: Graph renders with nodes, minimap visible
    Failure Indicators: Blank page, loading spinner stuck, no nodes rendered
    Evidence: .sisyphus/evidence/task-12-graph-page-render.png

  Scenario: Graph page shows error for textbook without graph
    Tool: Playwright
    Preconditions: Run "Playwright QA Environment Setup" steps 1-3 only (skip step 4 — do NOT generate graph). Create a second textbook via API without triggering graph generation. Record its textbook_id as noGraphTextbookId.
    Steps:
      1. Navigate to http://localhost:5173/graph/{noGraphTextbookId}
      2. Wait for content to load (timeout: 5s)
      3. Assert error message visible containing "generate" or "no graph"
    Expected Result: Clear error message with guidance to generate
    Failure Indicators: Blank page, unhandled error, no user guidance
    Evidence: .sisyphus/evidence/task-12-graph-page-no-data.png
  ```

  **Commit**: YES (groups with Tasks 13, 14)
  - Message: `feat(knowledge-graph): build graph page with expand/collapse and details panel`
  - Files: `frontend/src/pages/GraphPage.tsx`, `frontend/src/hooks/useKnowledgeGraph.ts`, `frontend/src/App.tsx`
  - Pre-commit: `cd frontend && npx vitest run`

- [x] 13. Concept Details Panel

  **What to do**:
  - Write RED vitest tests: test panel renders with concept data, test close behavior
  - Create `frontend/src/components/graph/ConceptDetailPanel.tsx`
  - Implement side panel (right-side, fixed width ~320px) that shows when a node is clicked:
    - Header: concept title + node_type badge (PixelBadge)
    - Description section: concept description text
    - Source section: "Found in: Chapter X, Section Y, Page Z" with clickable link
    - Relationships section: list of connected edges grouped by type (e.g., "Proves: [Theorem A]", "Used by: [Concept B, Concept C]")
    - LaTeX rendering: if concept has equations in metadata, render with KaTeX (InlineMath/BlockMath)
    - Close button (PixelButton secondary) or click outside to dismiss
  - Style with pixel-art design: PixelPanel wrapper, theme.css colors
  - Integrate into GraphPage: pass `selectedNodeId` state, render conditionally

  **Must NOT do**:
  - Do NOT navigate away from graph page on source link click (open in new tab or show tooltip)
  - Do NOT render panel when no node is selected
  - Do NOT put API calls in the panel component — receive data via props

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI component with pixel-art styling, KaTeX rendering, responsive layout
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12, 14, 15, 16)
  - **Blocks**: Task 19
  - **Blocked By**: Tasks 10, 12

  **References**:

  **Pattern References**:
  - `frontend/src/components/ExplanationView.tsx` — Shows side panel pattern with content rendering
  - `frontend/src/components/ContentRenderer.tsx` — Shows KaTeX + markdown rendering pattern
  - `frontend/src/components/pixel/PixelPanel.tsx` — Container styling
  - `frontend/src/components/pixel/PixelBadge.tsx` — Badge component for node_type

  **WHY Each Reference Matters**:
  - `ExplanationView.tsx`: Closest existing pattern — a side panel that displays detailed content with rich formatting
  - `ContentRenderer.tsx`: Shows how to render LaTeX in this project (react-katex + remark-math)

  **Acceptance Criteria**:

  - [ ] Panel renders concept title, description, source reference
  - [ ] Relationships grouped by type
  - [ ] KaTeX equations render correctly
  - [ ] Close button works
  - [ ] Panel hidden when no node selected
  - [ ] `npx vitest run src/components/graph/ConceptDetailPanel.test.tsx` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Details panel shows concept information on node click
    Tool: Playwright
    Preconditions: Graph page with nodes rendered
    Steps:
      1. Navigate to graph page
      2. Click on a concept node (selector: `.react-flow__node-concept`)
      3. Wait for details panel to appear (selector: `.concept-detail-panel`, timeout: 3s)
      4. Assert concept title is visible in panel
      5. Assert "Found in:" source reference is visible
      6. Take screenshot
    Expected Result: Panel appears with concept details
    Failure Indicators: No panel appears, empty content, panel covers graph
    Evidence: .sisyphus/evidence/task-13-detail-panel-click.png

  Scenario: Details panel closes correctly
    Tool: Playwright
    Preconditions: Details panel is open
    Steps:
      1. Click close button in panel
      2. Assert panel is no longer visible
    Expected Result: Panel disappears cleanly
    Failure Indicators: Panel stays visible, page state corrupted
    Evidence: .sisyphus/evidence/task-13-detail-panel-close.png
  ```

  **Commit**: YES (groups with Tasks 12, 14)
  - Message: `feat(knowledge-graph): build graph page with expand/collapse and details panel`
  - Files: `frontend/src/components/graph/ConceptDetailPanel.tsx`
  - Pre-commit: `cd frontend && npx vitest run`

- [x] 14. Multi-Level Expand/Collapse Logic

  **What to do**:
  - Write RED vitest tests: test expand/collapse state transitions, test node visibility
  - Create `frontend/src/hooks/useExpandCollapse.ts`
  - Implement expand/collapse behavior for multi-level graph:
    - Track expanded state per chapter node: `expandedChapters: Set<string>`
    - When chapter node collapsed: set `hidden: true` on all its child concept nodes AND their edges (React Flow's native hidden property)
    - When chapter node expanded: set `hidden: false` on child concept nodes
    - Double-click on concept node → expand to show equation-level nodes (if available)
    - Track `expandedConcepts: Set<string>` for equation-level expansion
    - Initial state: all chapters collapsed (only chapter-level nodes visible)
    - Provide `toggleChapter(nodeId)` and `toggleConcept(nodeId)` callbacks
  - Integrate with GraphPage: apply hidden property to nodes/edges before passing to React Flow
  - Re-run dagre layout when visibility changes (only on visible nodes)

  **Must NOT do**:
  - Do NOT use CSS `display: none` — MUST use React Flow's `hidden` property
  - Do NOT re-fetch data on expand/collapse — all data is already loaded, just toggle visibility
  - Do NOT animate transitions for MVP (can add later)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex state management with graph visibility, parent-child relationships, re-layout on change
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12, 13, 15, 16)
  - **Blocks**: Task 19
  - **Blocked By**: Tasks 11, 12

  **References**:

  **Pattern References**:
  - `frontend/src/hooks/usePanelLayout.ts` — Hook structure with state + callbacks
  - `frontend/src/hooks/useGraphLayout.ts` (Task 11) — Layout computation to re-run on expand/collapse

  **External References**:
  - React Flow `hidden` property: `nodes.map(n => ({ ...n, hidden: !expandedChapters.has(n.parentId) }))`

  **WHY Each Reference Matters**:
  - React Flow `hidden`: This is the ONLY correct way to show/hide nodes in React Flow. CSS display:none breaks edge rendering.

  **Acceptance Criteria**:

  - [ ] Initial state: only chapter-level nodes visible
  - [ ] Click chapter → child concepts appear
  - [ ] Click again → child concepts hide
  - [ ] Hidden nodes use React Flow `hidden` property (not CSS)
  - [ ] Layout recalculates for visible nodes only
  - [ ] `npx vitest run src/hooks/useExpandCollapse.test.ts` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Expand chapter reveals child concepts
    Tool: Playwright
    Preconditions: Graph page with 2+ chapter nodes, all collapsed
    Steps:
      1. Count visible nodes — assert only chapter nodes visible
      2. Click on first chapter node
      3. Wait 500ms for layout recalculation
      4. Count visible nodes — assert increased (concept nodes now visible)
      5. Assert new nodes are visually positioned below the clicked chapter
      6. Take screenshot
    Expected Result: Child concepts appear below chapter, graph re-layouts
    Failure Indicators: No new nodes appear, nodes overlap, layout doesn't update
    Evidence: .sisyphus/evidence/task-14-expand-chapter.png

  Scenario: Collapse chapter hides child concepts
    Tool: Playwright
    Preconditions: Chapter is expanded with visible concepts
    Steps:
      1. Click on the expanded chapter node
      2. Wait 500ms
      3. Assert concept nodes are no longer visible
      4. Assert edges to those concepts are also hidden
    Expected Result: Clean collapse, edges hidden too
    Failure Indicators: Nodes stay visible, orphan edges remain
    Evidence: .sisyphus/evidence/task-14-collapse-chapter.png
  ```

  **Commit**: YES (groups with Tasks 12, 13)
  - Message: `feat(knowledge-graph): build graph page with expand/collapse and details panel`
  - Files: `frontend/src/hooks/useExpandCollapse.ts`
  - Pre-commit: `cd frontend && npx vitest run`

- [x] 15. "Generate Relationship" Button + Navigation

  **What to do**:
  - Add "Generate Relationship" button to `frontend/src/components/CoursePreviewView.tsx`:
    - Place in `.preview-header` section, next to course title
    - Use `<PixelButton variant="primary">` matching existing button style
    - Disabled when no textbook is selected (`disabled={!selectedTextbookId}`)
    - Disabled when selected textbook has no extracted content (check pipeline status)
    - onClick: call `buildGraph(selectedTextbookId)` then navigate to `/graph/{selectedTextbookId}`
  - Add "View Graph" button: if graph already exists for textbook, show "View Graph" instead of "Generate"
    - Check graph existence: call `getGraphStatus(textbookId)` on textbook selection
    - If status='completed' → show "View Graph" (navigates directly)
    - If status='processing' → show "Generating..." (disabled)
    - If no graph → show "Generate Relationship"
  - Navigation: use `useNavigate()` from react-router-dom to go to `/graph/{textbookId}`

  **Must NOT do**:
  - Do NOT allow generation on textbooks without extracted content
  - Do NOT navigate before the build API call succeeds
  - Do NOT modify the three-panel layout structure

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Adding button + conditional logic to existing component — focused change
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12, 13, 14, 16)
  - **Blocks**: Task 16
  - **Blocked By**: Tasks 8, 9

  **References**:

  **Pattern References**:
  - `frontend/src/components/CoursePreviewView.tsx` — The file to modify. Look at existing PixelButton patterns in the preview-header section
  - `frontend/src/components/CoursePreviewView.tsx` `handleBeginStudy` — Follow this click handler pattern

  **WHY Each Reference Matters**:
  - `CoursePreviewView.tsx`: This IS the file being modified. The button goes in `.preview-header`, following the same PixelButton + onClick pattern as "Begin Study"

  **Acceptance Criteria**:

  - [ ] "Generate Relationship" button visible in coursepreview header
  - [ ] Button disabled when no textbook selected
  - [ ] Button disabled when textbook has no extracted content
  - [ ] Click triggers API call then navigates to graph page
  - [ ] "View Graph" shown when graph already exists
  - [ ] `npx tsc --noEmit` passes

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Generate button appears and triggers generation
    Tool: Playwright
    Preconditions: Backend running, course with textbook that has extracted content
    Steps:
      1. Navigate to http://localhost:5173/
      2. Click on course to open CoursePreviewView
      3. Select a textbook with extracted content
      4. Assert "Generate Relationship" button is visible and enabled
      5. Click "Generate Relationship"
      6. Assert navigation to /graph/{textbookId} occurs
    Expected Result: Button triggers generation and navigates to graph page
    Failure Indicators: Button missing, stays disabled, no navigation
    Evidence: .sisyphus/evidence/task-15-generate-button.png

  Scenario: Button disabled for textbook without content
    Tool: Playwright
    Preconditions: Course has textbook with pipeline_status != 'fully_extracted'
    Steps:
      1. Navigate to course preview
      2. Select textbook without extracted content
      3. Assert "Generate Relationship" button is disabled
    Expected Result: Button is visually disabled, not clickable
    Failure Indicators: Button is enabled, click triggers error
    Evidence: .sisyphus/evidence/task-15-button-disabled.png
  ```

  **Commit**: YES (groups with Task 16)
  - Message: `feat(knowledge-graph): add generate button and progress tracking`
  - Files: `frontend/src/components/CoursePreviewView.tsx`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

- [x] 16. Background Job Progress Tracking UI

  **What to do**:
  - On the graph page, if graph generation is in progress (status='processing'), show a progress indicator:
    - Display: "Generating knowledge graph... Chapter X of Y (Z%)"
    - Use `pollGraphStatus()` from API client to poll every 2 seconds
    - Show pixel-art progress bar (match existing pipeline progress patterns)
    - When completed: stop polling, fetch graph data, render graph
    - When failed: show error message with "Retry" button
  - Integrate into `GraphPage.tsx` and `useKnowledgeGraph.ts` hook:
    - On mount: check status first. If 'completed' → load graph. If 'processing' → start polling. If no job → show "Generate" prompt.
  - Add progress state to the hook: isGenerating, progressPct, processedChapters, totalChapters

  **Must NOT do**:
  - Do NOT poll faster than every 2 seconds
  - Do NOT continue polling after completed/failed status
  - Do NOT show raw error messages from backend

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Polling logic, state management, progress UI — multiple concerns
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12, 13, 14, 15)
  - **Blocks**: Tasks 18, 19
  - **Blocked By**: Tasks 8, 15

  **References**:

  **Pattern References**:
  - `frontend/src/components/CoursePreviewView.tsx` pipeline progress section — Shows how pipeline extraction progress is currently displayed (the pattern to follow)
  - `frontend/src/api/knowledgeGraph.ts` `pollGraphStatus()` (Task 9) — The polling function to use

  **WHY Each Reference Matters**:
  - Pipeline progress in CoursePreviewView: This is the EXACT UX pattern to follow — showing "Chapter X of Y" with status text during background processing

  **Acceptance Criteria**:

  - [ ] Progress indicator shows during generation
  - [ ] Chapters processed / total displayed
  - [ ] Polling stops on completion
  - [ ] Graph auto-renders after completion
  - [ ] Failed state shows error + retry button

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Progress tracking during graph generation
    Tool: Playwright
    Preconditions: Graph generation just triggered (status='processing')
    Steps:
      1. Navigate to /graph/{textbookId} while generation in progress
      2. Assert progress indicator visible (selector: `.graph-progress`)
      3. Wait 5s
      4. Assert progress percentage has increased
      5. Wait until generation completes (timeout: 120s)
      6. Assert graph renders automatically after completion
      7. Take screenshot of completed graph
    Expected Result: Smooth transition from progress → rendered graph
    Failure Indicators: Stuck progress, no auto-render, polling continues after done
    Evidence: .sisyphus/evidence/task-16-progress-tracking.png

  Scenario: Failed generation shows error with retry
    Tool: Playwright
    Preconditions: Graph generation failed (mock or real failure)
    Steps:
      1. Navigate to /graph/{textbookId} with failed job
      2. Assert error message visible
      3. Assert "Retry" button visible
    Expected Result: Clear error state with recovery option
    Failure Indicators: Blank page, no error message, no retry option
    Evidence: .sisyphus/evidence/task-16-failed-state.png
  ```

  **Commit**: YES (groups with Task 15)
  - Message: `feat(knowledge-graph): add generate button and progress tracking`
  - Files: `frontend/src/pages/GraphPage.tsx`, `frontend/src/hooks/useKnowledgeGraph.ts`
  - Pre-commit: `cd frontend && npx vitest run`

- [x] 17. Edge Styling by Relationship Type

  **What to do**:
  - Write RED vitest tests: test edge style mapping function
  - Create `frontend/src/components/graph/edgeStyles.ts`:
    - Map each of 9 relationship types to a distinct visual style:
      - `derives_from`: solid line, `--color-accent-pink` (#e94560), arrow marker
      - `proves`: bold solid line, `--color-text-accent`, arrow marker
      - `prerequisite_of`: dashed line, `--color-accent-amber` (#f5a623), arrow marker
      - `uses`: thin solid line, `--color-text-secondary`, arrow marker
      - `generalizes`: dotted line, blue-ish, bidirectional arrow
      - `specializes`: dotted line, blue-ish, arrow marker
      - `contradicts`: wavy/red line, `--color-danger` (#ff4444), double-headed arrow
      - `defines`: thick solid line, green-ish, arrow marker
      - `equivalent_form`: double solid line, `--color-accent-amber`, bidirectional
    - Export `getEdgeStyle(relationshipType: RelationshipType): EdgeProps` — returns React Flow edge configuration
    - Add edge labels showing relationship type (e.g., "derives from", "proves")
  - Add legend component: `GraphLegend.tsx` — shows color/style mapping for each relationship type
  - Add to `graph.css`: styles for each edge type using CSS classes

  **Must NOT do**:
  - Do NOT make all edges look the same — visual distinction is critical for understanding
  - Do NOT use colors that clash with the pixel-art theme

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Visual design — color selection, line styles, legend component
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 18, 19)
  - **Blocks**: Task 19
  - **Blocked By**: Task 12

  **References**:

  **Pattern References**:
  - `frontend/src/styles/theme.css` — Color variables to use
  - `frontend/src/components/pixel/PixelBadge.tsx` — Shows variant-based color coding pattern

  **External References**:
  - React Flow custom edges: `markerEnd: { type: MarkerType.ArrowClosed }`, `style: { stroke, strokeDasharray }`

  **Acceptance Criteria**:

  - [ ] All 9 relationship types have distinct visual styles
  - [ ] Edge labels visible
  - [ ] Legend component shows all types with visual examples
  - [ ] Colors from theme.css palette
  - [ ] `npx vitest run src/components/graph/edgeStyles.test.ts` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Edge styles visually distinguish relationship types
    Tool: Playwright
    Preconditions: Graph page with multiple edge types
    Steps:
      1. Navigate to graph page with diverse relationships
      2. Assert at least 3 different edge colors visible
      3. Assert edge labels visible on hover or always
      4. Assert legend component visible with all 9 types
      5. Take screenshot
    Expected Result: Edges are visually distinguishable, legend readable
    Failure Indicators: All edges same color, no labels, missing legend items
    Evidence: .sisyphus/evidence/task-17-edge-styles.png

  Scenario: Contradicts edges are distinctly alarming
    Tool: Playwright
    Preconditions: Graph has a "contradicts" edge
    Steps:
      1. Find the contradicts edge
      2. Assert it uses red/danger color
      3. Assert it has double-headed arrow
    Expected Result: Contradicts edges stand out visually
    Failure Indicators: Looks same as other edges
    Evidence: .sisyphus/evidence/task-17-contradicts-edge.png
  ```

  **Commit**: YES (groups with Tasks 18, 19)
  - Message: `feat(knowledge-graph): polish edge styles, error states, integration tests`
  - Files: `frontend/src/components/graph/edgeStyles.ts`, `frontend/src/components/graph/GraphLegend.tsx`, `frontend/src/styles/graph.css`
  - Pre-commit: `cd frontend && npx vitest run`

- [x] 18. Graph Page Loading States + Error Handling

  **What to do**:
  - Add comprehensive loading/error/empty states to GraphPage:
    - **Loading**: Pixel-art spinner or pulsing text "Loading knowledge graph..." while fetching data
    - **Empty graph**: "No knowledge graph generated yet. Go back and click 'Generate Relationship' to build one." with back button
    - **Generation in progress**: Progress tracking UI from Task 16
    - **Error**: "Failed to load knowledge graph: {error}. Try regenerating." with retry + back buttons
    - **No extracted content**: "This textbook hasn't been processed yet. Extract chapters first." with link back to coursepreview
  - Add error boundary around React Flow component to catch rendering errors
  - Handle network errors from API calls gracefully (try/catch in useKnowledgeGraph hook)
  - Style all states with pixel-art theme (PixelPanel containers, themed colors)

  **Must NOT do**:
  - Do NOT show raw error stack traces to users
  - Do NOT leave any state unhandled (every API call must have error handling)
  - Do NOT show browser default error pages

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple UI states, error boundary, network error handling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 17, 19)
  - **Blocks**: Task 19
  - **Blocked By**: Tasks 12, 16

  **References**:

  **Pattern References**:
  - `frontend/src/components/SplashScreen.tsx` — Shows loading/error state patterns used in this app
  - `frontend/src/pages/DeskPage.tsx` — Shows how loading states are handled in existing pages

  **Acceptance Criteria**:

  - [ ] All 5 states render correctly (loading, empty, progress, error, no content)
  - [ ] Error boundary catches React Flow crashes
  - [ ] All states use pixel-art styling
  - [ ] Back/retry buttons functional in all error states

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All error states render correctly
    Tool: Playwright
    Preconditions: Various textbook states (no graph, failed, no content)
    Steps:
      1. Navigate to /graph/{noGraphId} — assert "No knowledge graph" message
      2. Navigate to /graph/{noContentId} — assert "not processed" message  
      3. Assert back buttons are functional in each state
    Expected Result: Each state renders appropriate message with recovery action
    Failure Indicators: Blank page, generic error, no recovery path
    Evidence: .sisyphus/evidence/task-18-error-states.png

  Scenario: Network error handled gracefully
    Tool: Playwright
    Preconditions: Backend stopped/unreachable
    Steps:
      1. Navigate to graph page while backend is down
      2. Assert error message appears (not browser error)
      3. Assert retry button is present
    Expected Result: User-friendly error, not browser default
    Failure Indicators: Browser network error page, unhandled promise rejection
    Evidence: .sisyphus/evidence/task-18-network-error.png
  ```

  **Commit**: YES (groups with Tasks 17, 19)
  - Message: `feat(knowledge-graph): polish edge styles, error states, integration tests`
  - Files: `frontend/src/pages/GraphPage.tsx`, `frontend/src/hooks/useKnowledgeGraph.ts`
  - Pre-commit: `cd frontend && npx vitest run`

- [x] 19. Integration Test — Full Pipeline End-to-End

  **What to do**:
  - Write a comprehensive integration test that exercises the FULL pipeline:
    - Backend integration test (`backend/tests/test_knowledge_graph_integration.py`):
      1. Create a course + textbook in test DB
      2. Create chapters with extraction_status='extracted'
      3. Create mock description files with key_concepts and prerequisites
      4. POST to `/api/knowledge-graph/{textbookId}/build` — assert 202
      5. Poll `/api/knowledge-graph/{textbookId}/status` until completed
      6. GET `/api/knowledge-graph/{textbookId}/graph` — assert nodes and edges exist
      7. GET `/api/knowledge-graph/{textbookId}/node/{nodeId}` — assert detail returned
      8. Verify node count matches expectations
      9. Verify edge types include at least prerequisite_of (from prerequisites field)
      10. DELETE `/api/knowledge-graph/{textbookId}` — assert graph removed
  - Frontend integration test (vitest with React Testing Library):
      1. Test full GraphPage render with mocked API data
      2. Test expand/collapse cycle
      3. Test node click → details panel
  - Mock AIRouter responses in backend test to avoid real LLM calls

  **Must NOT do**:
  - Do NOT make real LLM API calls in tests — mock AIRouter
  - Do NOT depend on real textbook files — use test fixtures
  - Do NOT skip error case tests

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: End-to-end integration across multiple services, complex setup/teardown
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (last implementation task)
  - **Blocks**: F1-F4
  - **Blocked By**: All previous tasks

  **References**:

  **Pattern References**:
  - `backend/tests/test_content_extractor.py` — Shows integration test patterns with mock data
  - `backend/tests/test_mineru_spike.py` — Shows how test fixtures are structured

  **Acceptance Criteria**:

  - [ ] Backend integration test covers full lifecycle: build → poll → fetch → delete
  - [ ] Frontend integration test covers: render → expand → click → details
  - [ ] All tests mock LLM calls (no real API usage)
  - [ ] `cd backend && python -m pytest tests/test_knowledge_graph_integration.py -v` → PASS
  - [ ] `npx vitest run src/pages/GraphPage.test.tsx` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full backend pipeline produces valid graph
    Tool: Bash (pytest)
    Preconditions: Test database with mock textbook and descriptions
    Steps:
      1. Run full integration test
      2. Assert POST /build returns 202
      3. Assert polling reaches 'completed'
      4. Assert GET /graph returns nodes with correct types and edges with correct relationship types
      5. Assert DELETE removes all graph data
    Expected Result: Complete lifecycle works with mocked LLM
    Failure Indicators: Any assertion failure, timeout on polling, empty graph
    Evidence: .sisyphus/evidence/task-19-backend-integration.txt

  Scenario: Frontend renders complete graph interaction cycle
    Tool: Bash (vitest)
    Preconditions: Mocked API responses
    Steps:
      1. Render GraphPage with mock graph data (5 chapters, 15 concepts, 10 edges)
      2. Assert chapter nodes visible
      3. Simulate expand on chapter 1
      4. Assert concept nodes appear
      5. Simulate click on concept node
      6. Assert details panel renders with concept info
    Expected Result: Full UI interaction cycle works
    Failure Indicators: Render errors, missing nodes after expand, empty panel
    Evidence: .sisyphus/evidence/task-19-frontend-integration.txt
  ```

  **Commit**: YES (groups alone — final implementation commit)
  - Message: `feat(knowledge-graph): polish edge styles, error states, integration tests`
  - Files: `backend/tests/test_knowledge_graph_integration.py`, `frontend/src/pages/GraphPage.test.tsx`
  - Pre-commit: `cd backend && python -m pytest tests/ -v && cd ../frontend && npx vitest run`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns (reactflow, dagre without @dagrejs, Neo4j imports, nodesConnectable={true}). Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `npx tsc --noEmit` in frontend + `python -m pytest` in backend. Review all new files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check React Flow memoization: all custom node components must use `React.memo()`. Verify `nodeTypes` defined outside component. Check AIRouter usage (not direct API calls).
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real QA — Full User Flow** — `unspecified-high` (+ `playwright` skill)
  Start backend. Navigate to bookshelf → select course → select textbook with extracted content → click "Generate Relationship" → wait for completion → navigate to graph page. Verify: graph renders, nodes display, zoom/pan works, click node → details panel shows. Test expand/collapse. Test with textbook that has NO extracted content (should show error). Save screenshots to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance: no cross-textbook graphs, no graph editing, no Neo4j, no reactflow package. Detect unaccounted changes. Flag scope creep.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| After Task(s) | Commit Message | Files | Pre-commit |
|---------------|---------------|-------|------------|
| 1, 2 | `feat(knowledge-graph): add schema and models for concept nodes/edges` | storage.py, knowledge_graph_models.py | `pytest backend/tests/` |
| 3, 4, 5 | `feat(knowledge-graph): add frontend types, dependencies, and prompt templates` | types/, package.json, prompts/ | `npx tsc --noEmit` |
| 6, 7 | `feat(knowledge-graph): implement graph builder service and DB methods` | knowledge_graph_builder.py, storage.py | `pytest backend/tests/` |
| 8, 9 | `feat(knowledge-graph): add API router and frontend client` | routers/, api/ | `pytest && npx tsc --noEmit` |
| 10, 11 | `feat(knowledge-graph): create custom node components and layout utility` | components/graph/, hooks/ | `npx vitest run` |
| 12, 13, 14 | `feat(knowledge-graph): build graph page with expand/collapse and details panel` | pages/, components/graph/ | `npx vitest run` |
| 15, 16 | `feat(knowledge-graph): add generate button and progress tracking` | CoursePreviewView.tsx, App.tsx | `npx vitest run` |
| 17, 18, 19 | `feat(knowledge-graph): polish edge styles, error states, integration tests` | components/graph/, tests/ | `pytest && npx vitest run` |

---

## Success Criteria

### Verification Commands
```bash
# Backend tests
cd backend && python -m pytest tests/ -v  # Expected: ALL PASS

# Frontend type check
cd frontend && npx tsc --noEmit  # Expected: 0 errors

# Frontend tests
cd frontend && npx vitest run  # Expected: ALL PASS

# API smoke test
curl http://127.0.0.1:8000/api/knowledge-graph/{textbookId}/status  # Expected: 200 OK

# Graph generation trigger
curl -X POST http://127.0.0.1:8000/api/knowledge-graph/{textbookId}/build  # Expected: 202 Accepted with job_id
```

### Final Checklist
- [ ] All "Must Have" present (multi-level graph, 9 relationship types, details panel, progress tracking, source traceability)
- [ ] All "Must NOT Have" absent (no cross-textbook, no editing, no Neo4j, no old packages)
- [ ] All backend tests pass (`pytest`)
- [ ] All frontend tests pass (`vitest`)
- [ ] Type check passes (`tsc --noEmit`)
- [ ] Graph renders with 50+ nodes without lag
- [ ] Evidence files present in `.sisyphus/evidence/`
