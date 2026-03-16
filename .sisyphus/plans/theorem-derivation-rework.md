# Theorem-Derivation Knowledge Graph Rework

**Goal**: Replace the noisy equation-node + variable-cooccurrence graph with a curated graph where **key theorems/methods/results** are nodes and **derivation chains** are edges with intermediate steps as metadata.

**Before**: 390 nodes (189 equation), 7,003 edges (6,647 shared_variables) — useless hairball
**After**: ~10-20 key result nodes per chapter, ~5-15 derivation edges per chapter — focused, useful

---

## Architecture Summary

**Nodes** (3 levels):
- `chapter` — organizing container (kept from current)
- `section` — grouping by textbook section (kept, collapsible)
- `subsection` — **KEY RESULT**: theorem, method, formula, definition, result
  - `metadata_json`: `{ "defining_equation": "LaTeX string" }`

**Edges** (semantic only, NO structural `contains`):
- `derives_from` — **PRIMARY**: mathematical derivation chain
  - `metadata_json`: `{ "derivation_steps": ["step1 LaTeX", "step2 LaTeX", ...] }`
- `prerequisite_of`, `uses`, `equivalent_form`, `generalizes`, `specializes`, `proves`, `defines`, `contradicts` — secondary relationships (kept in enum, rarely used)

**Removed**:
- `shared_variables` relationship type — gone entirely
- `contains` relationship type — hierarchy uses `source_chapter_id`/`source_section_id` on nodes
- `equation` node level — no more individual equation nodes
- Phase 3 of builder (equation parsing + variable co-occurrence)
- `latex_parser.py` import from builder (file kept, just unused)
- `CONCEPT_EXTRACTION_PROMPT` — chapter-level extraction is redundant
- `RELATIONSHIP_EXTRACTION_PROMPT` — replaced by in-section derivation extraction

---

## Tasks

### Task 1: DB Migration — add metadata_json to concept_edges
**Files**: `backend/app/services/storage.py` (V4 migration block)
**Changes**:
- Add V4 migration: `ALTER TABLE concept_edges ADD COLUMN metadata_json TEXT`
- Follows existing V2/V3 migration pattern in `_ensure_schema()`
**Verification**: Run app, check `PRAGMA table_info(concept_edges)` shows `metadata_json`

### Task 2: Backend Models — update enums + add edge metadata
**Files**: `backend/app/models/knowledge_graph_models.py`
**Changes**:
- `NodeType`: Add `method`, `result`, `formula` alongside existing `theorem`, `definition`, `concept`, `lemma`, `example`
- `RelationshipType`: Remove `shared_variables`, `contains`
- `NodeLevel`: Remove `equation`
- `ConceptEdge`: Add `metadata: Optional[dict] = None`
**Verification**: `pytest backend/tests/test_knowledge_graph_models.py` passes

### Task 3: Storage — add metadata_json to edge CRUD
**Files**: `backend/app/services/storage.py`
**Changes**:
- `create_concept_edge()`: Add `metadata_json: str | None = None` parameter, include in INSERT
- `get_concept_edges()`: Return `metadata_json` column, parse to dict in response
- `get_node_detail()` (if exists): Include metadata_json in edge results
**Verification**: Unit test creates edge with metadata_json, reads it back correctly

### Task 4: LLM Prompt Rework — KEY_RESULT_EXTRACTION_PROMPT
**Files**: `backend/app/services/knowledge_graph_prompts.py`
**Changes**:
- Replace `SECTION_CONCEPT_PROMPT` with `KEY_RESULT_EXTRACTION_PROMPT`:
  - Input: section title, section path, parent concept, section text, equations text
  - Output JSON: `{ "key_results": [...], "derivations": [...] }`
  - Each key_result: title, node_type, defining_equation (LaTeX), description
  - Each derivation: source title, target title, description, derivation_steps[] (LaTeX strings)
  - Prompt MUST instruct: "ONLY include key theorems, named formulas, methods, definitions. Do NOT include every equation. Typically 2-6 key results per section."
- Remove `CONCEPT_EXTRACTION_PROMPT` (chapter-level extraction eliminated)
- Keep `RELATIONSHIP_EXTRACTION_PROMPT` for optional cross-section pass (rename to `CROSS_SECTION_RELATIONSHIP_PROMPT`)
- Add `parse_key_result_response()` parser
**Verification**: Parser correctly handles mock LLM responses with key_results + derivations

### Task 5: Builder Rework — new 2-phase pipeline
**Files**: `backend/app/services/knowledge_graph_builder.py`
**Changes**:
- **Phase 1** (0-30%): Create chapter nodes (unchanged)
- **Phase 2** (30-85%): Per-section extraction — NEW:
  - Create section nodes (structural)
  - Call LLM with `KEY_RESULT_EXTRACTION_PROMPT` per section
  - Create key result nodes (level=subsection) with `metadata_json` containing `defining_equation`
  - Create `derives_from` edges with `metadata_json` containing `derivation_steps`
  - Deduplicate key results by title across sections
  - Add `asyncio.gather` with semaphore (max 3 concurrent) for parallel LLM calls
- **Phase 3** (85-100%): Optional cross-section relationship pass (existing `_extract_relationships` simplified)
- **REMOVE**: All Phase 3 equation parsing code (lines 189-276)
- **REMOVE**: `latex_parser` import (EquationInfo, build_variable_cooccurrence, parse_equation)
- **REMOVE**: `_extract_concepts_from_description` method (chapter-level extraction)
**Verification**: `pytest backend/tests/test_knowledge_graph_builder.py` passes

### Task 6: API Endpoint — serialize edge metadata
**Files**: `backend/app/routers/knowledge_graph.py`
**Changes**:
- In graph data response, parse `metadata_json` on edges (same pattern as nodes)
- Edge response includes `metadata` dict field
**Verification**: GET `/api/knowledge-graph/{id}/graph` returns edges with metadata field

### Task 7: Frontend Types — update TS types
**Files**: `frontend/src/types/knowledgeGraph.ts`
**Changes**:
- `NodeType`: Add `'method' | 'result' | 'formula'`
- `RelationshipType`: Remove `'shared_variables' | 'contains'`
- `NodeLevel`: Remove `'equation'`
- `ConceptEdge`: Add `metadata?: Record<string, unknown>`
- Update type guards and arrays
**Verification**: `npx tsc --noEmit` passes

### Task 8: Frontend — Edge Click + DerivationPanel
**Files**: `frontend/src/pages/GraphPage.tsx`, `frontend/src/api/knowledgeGraph.ts`, `frontend/src/hooks/useKnowledgeGraph.ts`, NEW `frontend/src/components/graph/DerivationPanel.tsx`
**Changes**:
- **Metadata plumbing** (CRITICAL — Momus review callout):
  - `api/knowledgeGraph.ts`: Map backend `metadata_json` → `metadata` on ConceptEdge response
  - `useKnowledgeGraph.ts` → `mapEdgeToFlow()`: Include `metadata` in ReactFlow edge `data`
  - ReactFlow edge `data` must carry `{ relationshipType, confidence, metadata }` so DerivationPanel can read it
- Add `onEdgeClick` handler to ReactFlow in GraphPage
- Track `selectedEdgeId` state alongside `selectedNodeId`
- Create `DerivationPanel` component:
  - Shows source → target with derivation type
  - Renders each `derivation_step` with KaTeX (`react-katex` already installed)
  - Slide-in panel similar to ConceptDetailPanel
  - Clicking a node clears edge selection and vice versa
**Verification**: `npx tsc --noEmit` passes, visual test clicking an edge shows panel

### Task 9: Frontend — ConceptDetailPanel update
**Files**: `frontend/src/components/graph/ConceptDetailPanel.tsx`
**Changes**:
- Show `defining_equation` from node metadata using KaTeX rendering
- Remove equation-level specific sections (variables list, raw_latex display)
- Add description display for key results
- Show node_type badge with new types (method, result, formula)
**Verification**: `npx tsc --noEmit` passes

### Task 10: Frontend Cleanup — remove dead code
**Files**: `frontend/src/components/graph/edgeStyles.ts`, `frontend/src/components/graph/GraphLegend.tsx`, `frontend/src/hooks/useKnowledgeGraph.ts`, `frontend/src/hooks/useExpandCollapse.ts`, `frontend/src/components/graph/EquationNode.tsx`, `frontend/src/components/graph/nodeTypes.ts`
**Changes**:
- `edgeStyles.ts`: Remove `shared_variables` and `contains` entries
- `GraphLegend.tsx`: Remove shared_variables/contains from legend
- `useKnowledgeGraph.ts`: Remove `equation` type mapping in `mapNodeToFlow`
- `useExpandCollapse.ts`: Simplify — only chapter/section toggle (no equation level)
- `EquationNode.tsx`: Delete file
- `nodeTypes.ts`: Remove `equation` from nodeTypes map
**Verification**: `npx tsc --noEmit` passes, `npm run test` passes

### Task 11: Backend Tests — update for new model
**Files**: `backend/tests/test_knowledge_graph_builder.py`, `backend/tests/test_knowledge_graph_models.py`, `backend/tests/test_deep_graph_integration.py`
**Changes**:
- Update builder tests to mock new `KEY_RESULT_EXTRACTION_PROMPT` responses
- Test that key results are created with defining_equation in metadata
- Test that derives_from edges are created with derivation_steps in metadata
- Test that no equation nodes or shared_variables edges are created
- Update model tests for new enum values
- Update integration test for new pipeline
**Verification**: `pytest backend/tests/test_knowledge_graph_*.py` all pass

### Task 12: Frontend Tests — update for new types
**Files**: Frontend test files referencing graph types
**Changes**:
- Update mock data to remove `equation` level and `shared_variables` type
- Add test for DerivationPanel rendering with KaTeX
- Update ConceptDetailPanel tests for defining_equation display
- Remove EquationNode test file if it exists
**Verification**: `npm run test` all pass

### Task 13: Integration Test — end-to-end with mocked LLM
**Files**: `backend/tests/test_deep_graph_integration.py`
**Changes**:
- Mock LLM to return key_results + derivations format
- Verify builder creates correct node count (much fewer than before)
- Verify edges have derivation_steps in metadata
- Verify no shared_variables edges exist
- Verify graph is usable (not a hairball)
**Verification**: `pytest backend/tests/test_deep_graph_integration.py` passes

---

## Execution Order

Dependencies:
- T1 → T3 → T5 (DB → Storage → Builder)
- T2 → T4, T5, T7 (Models used everywhere)
- T4 → T5 (Prompts used by builder)
- T7 → T8, T9, T10 (Types before frontend)

Optimal wave execution:
1. **Wave 1** (foundations): T1 + T2 in parallel
2. **Wave 2** (backend core): T3 + T4 in parallel (both depend on T1/T2)
3. **Wave 3** (backend integration): T5 + T6 (depend on T3/T4)
4. **Wave 4** (frontend types): T7
5. **Wave 5** (frontend features): T8 + T9 + T10 in parallel
6. **Wave 6** (tests): T11 + T12 in parallel
7. **Wave 7** (integration): T13

---

## Constraints
- All work in worktree `C:\Local\Github\Lazy_Learn_stem\`
- No new dependencies (KaTeX already installed)
- No SymPy, no NetworkX
- TDD throughout
- `@xyflow/react` not `reactflow`, `@dagrejs/dagre` not `dagre`
- `nodeTypes` at module level, all node components `React.memo()`
- `nodesConnectable={false}` (read-only graph)
