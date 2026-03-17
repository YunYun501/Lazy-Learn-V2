# Equation Decomposition in Knowledge Graph

## TL;DR

> **Quick Summary**: Add a second enrichment pass to the knowledge graph builder that decomposes each equation into its component variables (classified as "calculated" or "constant"), stores structured breakdowns in node metadata, and displays them in an expanded ConceptDetailPanel with clickable links to related equation nodes.
> 
> **Deliverables**:
> - `MetadataStore.update_concept_node_metadata()` storage method
> - `EQUATION_ENRICHMENT_PROMPT` + `parse_enrichment_response()` parser
> - `KnowledgeGraphBuilder._enrich_equation_nodes()` pipeline phase
> - Expanded `ConceptDetailPanel` with "Equation Breakdown" section
> - CSS styling for breakdown section
> - Full TDD test suite across all layers
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Task 1 → Task 3 → Task 5 → Task 7 → Task 8

---

## Context

### Original Request
When clicking an equation node in the knowledge graph (e.g. endurance limit σ_e = k_a·k_b·k_c·k_d·k_e·k_g·σ'_e), show a breakdown of each component variable with descriptions. Variables that produce other variables (have their own equation) should be linked/clickable. Constants should have page citations and values with rationale. Must work generically for ALL equations.

### Interview Summary
**Key Discussions**:
- **Modeling**: Metadata enrichment on existing nodes — NOT new nodes per variable. User: "too difficult to have a huge graph with all the equations"
- **Two-pass approach**: First pass = existing graph build. Second pass = automatic enrichment analyzing each equation's variables via LLM
- **Calculated variables**: Show their equation + link to existing node if one exists
- **Constants**: Cite exact page/definition + give value with rationale (e.g., "k_b = 1.5 because shaft diameter > 51mm")
- **Frontend**: Expand existing ConceptDetailPanel with "Equation Breakdown" section
- **Trigger**: Automatic after graph build — single "Generate" button
- **Retroactive**: Only new graphs — no enrichment of existing ones
- **Testing**: TDD approach

### Metis Review
**Identified Gaps** (addressed):
- **No `update_concept_node_metadata()` in MetadataStore** — prerequisite task added (Task 1)
- **LLM variable classification inconsistency** — pass all existing node titles + IDs to enrichment prompt for cross-referencing
- **Node title matching brittleness** — let LLM return exact `node_id` from provided list, not fuzzy title match
- **Progress bar disruption** — adjust progress bands to include enrichment phase
- **Enrichment cost scaling** — batch 3-5 equations per LLM call using existing semaphore pattern
- **Edge case: node not found for calculated variable** — mark as "calculated" without link (frontend shows equation but no navigation)
- **Edge case: LLM failure** — graceful skip with try/except pattern, matching existing builder error handling

---

## Work Objectives

### Core Objective
Enable equation nodes in the knowledge graph to display a structured breakdown of their component variables, with clickable navigation for calculated variables and contextual descriptions for constants.

### Concrete Deliverables
- `backend/app/services/storage.py` — new `update_concept_node_metadata()` method
- `backend/app/services/knowledge_graph_prompts.py` — new `EQUATION_ENRICHMENT_PROMPT` + `parse_enrichment_response()`
- `backend/app/services/knowledge_graph_builder.py` — new `_enrich_equation_nodes()` method wired into `build_graph()`
- `frontend/src/components/graph/ConceptDetailPanel.tsx` — new "Equation Breakdown" section
- `frontend/src/styles/graph.css` — breakdown section styling
- Test files: `test_storage_update.py`, `test_equation_enrichment_prompts.py`, `test_equation_enrichment.py`, updated `ConceptDetailPanel.test.tsx`

### Definition of Done
- [ ] `pytest backend/tests/ -v --tb=short` → all pass (0 failures)
- [ ] `npx vitest run --reporter=verbose` → all pass (0 failures)
- [ ] Clicking an equation node with enrichment data shows breakdown with variables
- [ ] Calculated variables are clickable → navigate to linked node
- [ ] Constants show description + page reference
- [ ] Nodes without enrichment data show existing behavior (no crash, no empty section)

### Must Have
- Enrichment runs automatically as part of graph build (no separate button)
- Variables classified as "calculated" (has own equation) vs "constant" (fixed value/chosen parameter)
- Calculated variables link to existing graph nodes when match is found
- Constants display page reference and brief description/rationale
- Graceful degradation: enrichment failure doesn't crash the graph build
- Graceful frontend: no breakdown section for nodes without enrichment data

### Must NOT Have (Guardrails)
- **NO new graph nodes for variables** — enrichment data lives in `metadata.equation_components`
- **NO new API endpoints** — metadata flows through existing `getNodeDetail()`
- **NO modification to `KEY_RESULT_EXTRACTION_PROMPT`** — enrichment uses its own new prompt
- **NO changes to `ConceptNode` TypeScript interface or Pydantic model** — `metadata` is already flexible
- **NO retroactive enrichment** — only newly generated graphs
- **NO new `RelationshipType` or `NodeType` enum values** — existing enums unchanged
- **NO new edges created by enrichment** — topology stays the same
- **NO interactive editing** of variable classifications by the user
- **NO variable search/filter across the graph**
- **NO LaTeX parser enhancements** — LLM is the classifier, parser is only a hint

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest backend, vitest frontend)
- **Automated tests**: TDD — RED (failing test) → GREEN (minimal impl) → REFACTOR
- **Framework**: pytest (backend), vitest (frontend)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Backend**: Use Bash (pytest) — run test suite, assert outputs
- **Frontend/UI**: Use Playwright (browser) — navigate to graph, click equation node, verify breakdown renders
- **API**: Use Bash (curl) — hit graph endpoints, check metadata in response

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation):
├── Task 1: Storage update method [quick] (TDD)
├── Task 2: Enrichment prompt + parser [quick] (TDD)
└── Task 3: Frontend equation breakdown component [quick] (TDD)

Wave 2 (After Wave 1 — integration):
├── Task 4: Wire enrichment into KnowledgeGraphBuilder [deep] (depends: 1, 2)
├── Task 5: Frontend integration + clickable navigation [unspecified-high] (depends: 3)
└── Task 6: CSS styling for breakdown section [quick] (depends: 3)

Wave 3 (After Wave 2 — verification):
├── Task 7: Integration test — full pipeline [deep] (depends: 4, 5)
└── Task 8: End-to-end QA [unspecified-high] (depends: 7)

Wave FINAL (After ALL tasks — review):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
├── Task F3: Real manual QA via Playwright [unspecified-high]
└── Task F4: Scope fidelity check [deep]

Critical Path: Task 1 → Task 4 → Task 7 → F1-F4
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 3 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 | — | 4 |
| 2 | — | 4 |
| 3 | — | 5, 6 |
| 4 | 1, 2 | 7 |
| 5 | 3 | 7 |
| 6 | 3 | 8 |
| 7 | 4, 5 | 8 |
| 8 | 6, 7 | F1-F4 |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 → `quick`, T2 → `quick`, T3 → `quick`
- **Wave 2**: 3 tasks — T4 → `deep`, T5 → `unspecified-high`, T6 → `quick`
- **Wave 3**: 2 tasks — T7 → `deep`, T8 → `unspecified-high`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Storage: Add `update_concept_node_metadata()` to MetadataStore (TDD)

  **What to do**:
  - RED: Write `backend/tests/test_storage_update.py` with tests for:
    - `update_concept_node_metadata(node_id, metadata_json)` updates the `metadata_json` column in `concept_nodes` table
    - Returns silently if node_id doesn't exist (no error)
    - Preserves all other columns unchanged
    - Handles empty JSON `"{}"` and complex nested JSON
  - GREEN: Add `async def update_concept_node_metadata(self, node_id: str, metadata_json: str) -> None` to `MetadataStore` class in `backend/app/services/storage.py`
    - Simple SQL: `UPDATE concept_nodes SET metadata_json = ? WHERE id = ?`
  - REFACTOR: Ensure method follows the same `aiosqlite` pattern as other MetadataStore methods

  **Must NOT do**:
  - DO NOT add any other columns or modify the schema
  - DO NOT change existing MetadataStore methods

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - Simple single-method addition with straightforward SQL

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Task 4
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `backend/app/services/storage.py:152-1086` — MetadataStore class, follow the `async with aiosqlite.connect(self.db_path)` pattern used by all methods
  - `backend/app/services/storage.py` — look for `create_concept_node` method to see the existing `metadata_json` column handling

  **Test References**:
  - `backend/tests/test_knowledge_graph_builder.py:11-15` — `store` fixture pattern using `tmp_path`
  - `backend/tests/test_knowledge_graph_integration.py:20-24` — `_make_store` helper

  **Acceptance Criteria**:
  - [ ] Test file created: `backend/tests/test_storage_update.py`
  - [ ] `pytest backend/tests/test_storage_update.py -v` → PASS (4+ tests, 0 failures)
  - [ ] Method exists: `MetadataStore.update_concept_node_metadata(node_id, metadata_json)`
  - [ ] After calling update, `get_concept_node(node_id)` returns updated metadata

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Happy path — update existing node metadata
    Tool: Bash (pytest)
    Preconditions: MetadataStore initialized with tmp_path, one concept node created with empty metadata
    Steps:
      1. Call `store.create_concept_node(...)` with `metadata_json='{"old": true}'`
      2. Call `store.update_concept_node_metadata(node_id, '{"equation_components": [{"symbol": "k_a", "name": "surface factor"}]}')`
      3. Call `store.get_concept_node(node_id)` (or equivalent query)
      4. Assert returned metadata contains `equation_components` key
    Expected Result: `metadata_json` column contains the new JSON, other columns unchanged
    Evidence: .sisyphus/evidence/task-1-update-metadata.txt

  Scenario: Edge case — update non-existent node
    Tool: Bash (pytest)
    Preconditions: MetadataStore initialized with tmp_path, no nodes
    Steps:
      1. Call `store.update_concept_node_metadata("nonexistent-id", '{"test": true}')`
      2. Assert no exception raised
    Expected Result: Method returns silently, no crash
    Evidence: .sisyphus/evidence/task-1-nonexistent-node.txt
  ```

  **Commit**: YES
  - Message: `feat(storage): add update_concept_node_metadata method`
  - Files: `backend/app/services/storage.py`, `backend/tests/test_storage_update.py`
  - Pre-commit: `pytest backend/tests/test_storage_update.py -v`

- [x] 2. Prompts: Add equation enrichment prompt + parser (TDD)

  **What to do**:
  - RED: Write `backend/tests/test_equation_enrichment_prompts.py` with tests for:
    - `EQUATION_ENRICHMENT_PROMPT` template renders with placeholders: `{equation_latex}`, `{section_text}`, `{existing_nodes_json}`
    - `parse_enrichment_response(raw)` extracts `equation_components` list from LLM JSON
    - Parser handles: valid JSON, JSON wrapped in code blocks, malformed JSON (returns empty list), dict with `equation_components` key, raw list
    - Each component has schema: `symbol: str`, `name: str`, `type: "calculated"|"constant"`, `description: str`, `latex: str|null`, `page_reference: str|null`, `linked_node_id: str|null`
  - GREEN: Add to `backend/app/services/knowledge_graph_prompts.py`:
    - `EQUATION_ENRICHMENT_PROMPT` — prompt that receives: the equation's LaTeX, surrounding section text, and a JSON list of all existing node titles + IDs in the graph. Asks LLM to identify each variable/factor, classify as calculated/constant, provide description, and if calculated, return the exact `node_id` from the provided list.
    - `parse_enrichment_response(raw) -> list[dict]` — defensive parser following existing `parse_key_result_response` pattern
  - REFACTOR: Ensure prompt follows the same structure as existing prompts (clear instructions, JSON schema, examples)

  **Must NOT do**:
  - DO NOT modify `KEY_RESULT_EXTRACTION_PROMPT` or `CROSS_SECTION_RELATIONSHIP_PROMPT`
  - DO NOT add new relationship types or node types

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - Prompt template + JSON parser, following existing patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Task 4
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `backend/app/services/knowledge_graph_prompts.py:43-115` — `KEY_RESULT_EXTRACTION_PROMPT` format: section context + instructions + JSON schema + example
  - `backend/app/services/knowledge_graph_prompts.py:118-141` — `_strip_code_blocks()` + `parse_relationship_response()` defensive parsing pattern
  - `backend/app/services/knowledge_graph_prompts.py:144-190` — `parse_key_result_response()` handling multiple input types (dict, str, malformed)

  **Test References**:
  - `backend/tests/test_knowledge_graph_prompts.py:41-209` — `TestKeyResultParser` class: thorough test cases for parser with valid JSON, code blocks, malformed, missing keys

  **External References**:
  - The prompt should instruct the LLM to return JSON like: `{"equation_components": [{"symbol": "k_a", "name": "surface factor", "type": "constant", "description": "Accounts for surface finish...", "latex": null, "page_reference": "p.312", "linked_node_id": null}, {"symbol": "\\sigma'_e", "name": "endurance limit of test specimen", "type": "calculated", "description": "Base endurance limit from rotating-beam tests", "latex": "\\sigma'_e = 0.5 S_{ut}", "page_reference": null, "linked_node_id": "uuid-of-existing-node"}]}`

  **Acceptance Criteria**:
  - [ ] Test file created: `backend/tests/test_equation_enrichment_prompts.py`
  - [ ] `pytest backend/tests/test_equation_enrichment_prompts.py -v` → PASS (8+ tests, 0 failures)
  - [ ] `EQUATION_ENRICHMENT_PROMPT` exists and renders with placeholders
  - [ ] `parse_enrichment_response()` returns `list[dict]` with correct schema

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Happy path — parse valid enrichment JSON
    Tool: Bash (pytest)
    Preconditions: None
    Steps:
      1. Call `parse_enrichment_response('{"equation_components": [{"symbol": "k_a", "name": "surface factor", "type": "constant", "description": "...", "latex": null, "page_reference": "p.312", "linked_node_id": null}]}')`
      2. Assert result is a list with 1 element
      3. Assert element has all required keys: symbol, name, type, description
    Expected Result: Returns `[{"symbol": "k_a", "name": "surface factor", "type": "constant", ...}]`
    Evidence: .sisyphus/evidence/task-2-parse-valid.txt

  Scenario: Failure — malformed JSON returns empty list
    Tool: Bash (pytest)
    Preconditions: None
    Steps:
      1. Call `parse_enrichment_response('this is not json at all')`
      2. Assert result is empty list `[]`
    Expected Result: No exception, returns `[]`
    Evidence: .sisyphus/evidence/task-2-parse-malformed.txt
  ```

  **Commit**: YES
  - Message: `feat(prompts): add equation enrichment prompt and parser`
  - Files: `backend/app/services/knowledge_graph_prompts.py`, `backend/tests/test_equation_enrichment_prompts.py`
  - Pre-commit: `pytest backend/tests/test_equation_enrichment_prompts.py -v`

- [x] 3. Frontend: Equation breakdown component in ConceptDetailPanel (TDD)

  **What to do**:
  - RED: Add tests to `frontend/src/components/graph/ConceptDetailPanel.test.tsx`:
    - "Equation Breakdown" section renders when `metadata.equation_components` is a non-empty array
    - Section is hidden when `equation_components` is absent or empty array
    - Each calculated variable renders its LaTeX via `<BlockMath>` and has a clickable element
    - Each constant renders its description and page reference (no clickable link)
    - Clicking a calculated variable calls the `onClose` + opens a new node (via callback)
    - Invalid/unparseable LaTeX in a component doesn't crash the panel (error boundary or try/catch)
  - GREEN: Add an `EquationBreakdown` section inside `ConceptDetailPanel.tsx`:
    - Placed after the existing `defining_equation` section (line 71)
    - Reads `detail.node.metadata?.equation_components` as `Array<{symbol, name, type, description, latex, page_reference, linked_node_id}>`
    - Renders a list: each variable gets an icon (🔗 calculated, 📌 constant), its symbol + name, description
    - Calculated: shows `<BlockMath>` for its `latex`, wraps in a clickable div that calls a new prop `onNavigateToNode(linked_node_id)`
    - Constant: shows `page_reference` and description text
    - Wrap individual `<BlockMath>` in error boundary to prevent single bad LaTeX from crashing entire panel
  - REFACTOR: Extract `EquationBreakdown` as a sub-component if it exceeds 40 lines

  **Must NOT do**:
  - DO NOT add new API endpoints
  - DO NOT change the `ConceptNode` TypeScript interface
  - DO NOT add new React Flow node types

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - Extending existing React component with new section

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Tasks 5, 6
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `frontend/src/components/graph/ConceptDetailPanel.tsx:64-71` — existing `defining_equation` section: conditional render from metadata, `<BlockMath math={...} />`
  - `frontend/src/components/graph/ConceptDetailPanel.tsx:72-88` — existing relationships section: `<ul>` with `<li>` per edge, title lookups from `titleById` map
  - `frontend/src/components/graph/ConceptDetailPanel.tsx:8-13` — component props interface

  **Test References**:
  - `frontend/src/components/graph/ConceptDetailPanel.test.tsx` — existing tests: `makeDetail()` factory, mock `getNodeDetail`, render assertions

  **External References**:
  - `react-katex` docs: `<BlockMath math="..." />` for display math, wrapping in try/catch or ErrorBoundary for invalid LaTeX

  **Acceptance Criteria**:
  - [ ] New tests in: `frontend/src/components/graph/ConceptDetailPanel.test.tsx`
  - [ ] `npx vitest run src/components/graph/ConceptDetailPanel.test.tsx` → PASS (existing + 6+ new tests)
  - [ ] Breakdown section renders for enriched nodes
  - [ ] Breakdown section hidden for non-enriched nodes

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Happy path — equation breakdown with mixed variables
    Tool: Bash (vitest)
    Preconditions: Mock getNodeDetail returns node with metadata.equation_components = [{symbol: "k_a", name: "surface factor", type: "constant", description: "Accounts for surface finish", page_reference: "p.312", linked_node_id: null}, {symbol: "σ'_e", name: "endurance limit of test specimen", type: "calculated", description: "Base endurance limit", latex: "\\sigma'_e = 0.5 S_{ut}", linked_node_id: "uuid-123"}]
    Steps:
      1. Render ConceptDetailPanel with the mocked node
      2. Assert heading "Equation Breakdown" is visible
      3. Assert "surface factor" text appears
      4. Assert "p.312" text appears for the constant
      5. Assert "endurance limit of test specimen" text appears
      6. Assert clickable element exists for σ'_e (linked_node_id = "uuid-123")
    Expected Result: Both variables render correctly with their respective types
    Evidence: .sisyphus/evidence/task-3-breakdown-renders.txt

  Scenario: Edge case — no equation_components hides section
    Tool: Bash (vitest)
    Preconditions: Mock getNodeDetail returns node without equation_components in metadata
    Steps:
      1. Render ConceptDetailPanel
      2. Assert "Equation Breakdown" heading is NOT in the document
    Expected Result: No breakdown section rendered
    Evidence: .sisyphus/evidence/task-3-no-breakdown.txt
  ```

  **Commit**: NO (groups with Task 5, 6 in commit 4)

- [x] 4. Backend: Wire enrichment into KnowledgeGraphBuilder pipeline (TDD)

  **What to do**:
  - RED: Write `backend/tests/test_equation_enrichment.py` with tests for:
    - `_enrich_equation_nodes()` calls LLM for each node with non-empty `defining_equation` in metadata
    - Nodes without `defining_equation` are skipped (no LLM call)
    - LLM failure for one node doesn't prevent enrichment of other nodes
    - Enriched metadata is stored via `update_concept_node_metadata()`
    - `build_graph()` calls `_enrich_equation_nodes()` after section processing
    - Progress bar includes enrichment phase (85% → 95% for enrichment)
    - The enrichment prompt receives the equation's LaTeX, section text, and ALL existing node titles+IDs
    - Enrichment correctly passes existing node list so LLM can return `linked_node_id` values
  - GREEN: Add to `KnowledgeGraphBuilder`:
    - `async def _enrich_equation_nodes(self, textbook_id: str, all_nodes: list[dict]) -> None`
    - Query all concept nodes for the textbook that have a non-empty `defining_equation` in metadata
    - For each, build enrichment prompt with: equation LaTeX, section text (from source section), list of all existing nodes (id + title)
    - Call `ai_router.get_json_response(prompt)`, parse with `parse_enrichment_response()`
    - Call `store.update_concept_node_metadata(node_id, updated_metadata_json)`
    - Use `try/except → continue` pattern per node (line 104-108 pattern)
    - Use semaphore for concurrency (existing pattern)
  - Wire into `build_graph()`: call `_enrich_equation_nodes()` AFTER `asyncio.gather(*tasks)` (line 250) and BEFORE `_extract_relationships()` (line 255)
  - Adjust progress: section processing goes to 0.80, enrichment 0.80→0.90, cross-section 0.90→1.0

  **Must NOT do**:
  - DO NOT create new nodes or edges during enrichment
  - DO NOT modify the existing section processing logic
  - DO NOT skip `_extract_relationships()` — enrichment is inserted BEFORE it

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []
    - Complex async pipeline integration requiring understanding of the full build flow

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 7
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `backend/app/services/knowledge_graph_builder.py:67-241` — `process_section()` async function: semaphore, LLM call, parse, store. The enrichment follows this exact pattern
  - `backend/app/services/knowledge_graph_builder.py:104-108` — LLM error handling: `try: raw = await self.ai_router.get_json_response(prompt); parsed = parse_...(raw) except Exception: parsed = default`
  - `backend/app/services/knowledge_graph_builder.py:243-257` — the section where enrichment gets wired in: after `gather(*tasks)`, before `_extract_relationships()`
  - `backend/app/services/knowledge_graph_builder.py:273-320` — `_extract_relationships()` pattern: iterate nodes, build prompt, call LLM, parse, store

  **API/Type References**:
  - `backend/app/services/storage.py` — `update_concept_node_metadata()` (from Task 1)
  - `backend/app/services/knowledge_graph_prompts.py` — `EQUATION_ENRICHMENT_PROMPT`, `parse_enrichment_response()` (from Task 2)

  **Test References**:
  - `backend/tests/test_knowledge_graph_builder.py` — existing builder tests: AsyncMock for ai_router, store fixture, monkeypatch

  **Acceptance Criteria**:
  - [ ] Test file created: `backend/tests/test_equation_enrichment.py`
  - [ ] `pytest backend/tests/test_equation_enrichment.py -v` → PASS (6+ tests, 0 failures)
  - [ ] `_enrich_equation_nodes()` method exists on KnowledgeGraphBuilder
  - [ ] `build_graph()` calls enrichment after section processing
  - [ ] LLM failure in enrichment doesn't set job status to "failed"

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Happy path — enrichment stores equation_components in metadata
    Tool: Bash (pytest)
    Preconditions: MetadataStore with tmp_path, mock ai_router returns valid enrichment JSON with 3 components
    Steps:
      1. Create a textbook, chapter, and run build_graph() with mocked section content containing an equation
      2. After completion, query the equation node's metadata
      3. Assert metadata contains `equation_components` key
      4. Assert `equation_components` is a list with expected number of items
      5. Assert job status is "completed" (not "failed")
    Expected Result: Node metadata enriched with structured variable breakdown
    Evidence: .sisyphus/evidence/task-4-enrichment-stored.txt

  Scenario: Failure — LLM error during enrichment doesn't crash build
    Tool: Bash (pytest)
    Preconditions: Mock ai_router raises Exception on enrichment call
    Steps:
      1. Run build_graph() with the failing mock
      2. Assert job status is "completed" (enrichment failure is non-fatal)
      3. Assert nodes exist but without equation_components in metadata
    Expected Result: Graph build succeeds, enrichment gracefully skipped
    Evidence: .sisyphus/evidence/task-4-enrichment-failure.txt
  ```

  **Commit**: YES
  - Message: `feat(graph): wire equation enrichment into build pipeline`
  - Files: `backend/app/services/knowledge_graph_builder.py`, `backend/tests/test_equation_enrichment.py`
  - Pre-commit: `pytest backend/tests/test_equation_enrichment.py -v`

- [x] 5. Frontend: Wire clickable navigation for calculated variables

  **What to do**:
  - The `ConceptDetailPanel` currently takes `onClose` callback. It needs a way to navigate to another node when a calculated variable is clicked.
  - In `GraphPage.tsx`: pass `setSelectedNodeId` as a new prop `onNavigateToNode` to `ConceptDetailPanel`
  - In `ConceptDetailPanel.tsx`: when a calculated variable with `linked_node_id` is clicked, call `onNavigateToNode(linked_node_id)` — this updates the selected node, triggering the panel to reload with the new node's details
  - Add test: clicking a calculated variable fires `onNavigateToNode` with the correct `linked_node_id`
  - Add test: constant variables do NOT have clickable links

  **Must NOT do**:
  - DO NOT change React Flow node types
  - DO NOT add new state management or context

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
    - Integration wiring between GraphPage and ConceptDetailPanel

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 6)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 7
  - **Blocked By**: Task 3

  **References**:

  **Pattern References**:
  - `frontend/src/pages/GraphPage.tsx:48-51` — `handleNodeClick` sets `selectedNodeId` — same pattern for navigation
  - `frontend/src/pages/GraphPage.tsx:184-189` — `ConceptDetailPanel` usage with current props: `textbookId`, `nodeId`, `nodes`, `onClose`
  - `frontend/src/components/graph/ConceptDetailPanel.tsx:8-13` — current props interface — add `onNavigateToNode?: (nodeId: string) => void`

  **Acceptance Criteria**:
  - [ ] `ConceptDetailPanel` accepts `onNavigateToNode` prop
  - [ ] `GraphPage` passes `setSelectedNodeId` as `onNavigateToNode`
  - [ ] Clicking calculated variable calls `onNavigateToNode` with correct `linked_node_id`
  - [ ] `npx vitest run src/components/graph/ConceptDetailPanel.test.tsx` → PASS

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Happy path — click calculated variable navigates to its node
    Tool: Bash (vitest)
    Preconditions: Render ConceptDetailPanel with onNavigateToNode spy and enriched node data
    Steps:
      1. Find the clickable element for a calculated variable (type="calculated", linked_node_id="uuid-123")
      2. Fire click event
      3. Assert onNavigateToNode was called with "uuid-123"
    Expected Result: Navigation callback fires with correct node ID
    Evidence: .sisyphus/evidence/task-5-click-navigate.txt

  Scenario: Edge case — calculated variable without linked_node_id shows equation but no link
    Tool: Bash (vitest)
    Preconditions: Render with calculated variable where linked_node_id is null
    Steps:
      1. Find the variable's element
      2. Assert it renders the equation via BlockMath
      3. Assert it does NOT have a clickable link/button
    Expected Result: Equation shown but not clickable
    Evidence: .sisyphus/evidence/task-5-no-link.txt
  ```

  **Commit**: NO (groups with Task 3, 6 in commit 4)

- [x] 6. CSS: Style equation breakdown section

  **What to do**:
  - Add CSS rules to `frontend/src/styles/graph.css` for the equation breakdown section
  - Follow existing BEM pattern: `concept-detail-panel__breakdown`, `concept-detail-panel__variable`, `concept-detail-panel__variable--calculated`, `concept-detail-panel__variable--constant`
  - Calculated variables get a subtle highlight/hover effect to indicate they're clickable
  - Constants get a muted style with the page reference as a small badge
  - Each variable row: symbol (bold, monospace), name, description on next line
  - Ensure KaTeX equations don't overflow the panel width (add `overflow-x: auto` on equation containers)
  - Match existing pixel/retro aesthetic of the app

  **Must NOT do**:
  - DO NOT change existing CSS classes
  - DO NOT add external CSS libraries

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - CSS additions following existing BEM pattern

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 5)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 8
  - **Blocked By**: Task 3

  **References**:

  **Pattern References**:
  - `frontend/src/styles/graph.css` — existing BEM classes: `.concept-detail-panel`, `.concept-detail-panel__header`, `.concept-detail-panel__title`, `.concept-detail-panel__badge`, `.concept-detail-panel__description`, `.concept-detail-panel__relations`, `.concept-detail-panel__equation`

  **Acceptance Criteria**:
  - [ ] New CSS classes in `graph.css` following BEM pattern
  - [ ] Calculated variables have hover effect
  - [ ] KaTeX equations don't overflow panel width
  - [ ] Visual consistency with existing panel styles

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Visual verification — breakdown section styled correctly
    Tool: Playwright (browser)
    Preconditions: App running, graph generated with enriched equation nodes
    Steps:
      1. Navigate to graph page for a textbook
      2. Click on an equation node
      3. Screenshot the ConceptDetailPanel showing the equation breakdown
      4. Verify calculated variables have visible hover effect (hover over one, screenshot)
      5. Verify constant variables have page reference badge visible
    Expected Result: Breakdown section matches existing panel aesthetic, no overflow
    Evidence: .sisyphus/evidence/task-6-breakdown-styled.png
  ```

  **Commit**: YES (combined with Tasks 3, 5)
  - Message: `feat(ui): add equation breakdown section to ConceptDetailPanel`
  - Files: `frontend/src/components/graph/ConceptDetailPanel.tsx`, `frontend/src/components/graph/ConceptDetailPanel.test.tsx`, `frontend/src/styles/graph.css`, `frontend/src/pages/GraphPage.tsx`
  - Pre-commit: `npx vitest run src/components/graph/ConceptDetailPanel.test.tsx`

- [x] 7. Integration: Full pipeline test — build graph with enrichment (TDD)

  **What to do**:
  - Write an integration test that exercises the FULL pipeline: graph build → enrichment → API query → verify enriched metadata in response
  - Add to `backend/tests/test_equation_enrichment.py` or create `backend/tests/test_enrichment_integration.py`
  - Test flow:
    1. Create textbook + chapter + sections with equation content
    2. Mock `ai_router` to return realistic data for BOTH key result extraction AND enrichment
    3. Run `build_graph()`
    4. Query the graph via `get_concept_nodes()` or `get_node_detail()`
    5. Assert enriched nodes have `equation_components` in metadata
    6. Assert non-equation nodes DON'T have `equation_components`
    7. Assert `linked_node_id` values reference real node IDs in the graph

  **Must NOT do**:
  - DO NOT use real LLM calls — mock everything
  - DO NOT test frontend — this is backend-only integration

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []
    - Complex async integration test requiring full pipeline understanding

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 8
  - **Blocked By**: Tasks 4, 5

  **References**:

  **Pattern References**:
  - `backend/tests/test_knowledge_graph_integration.py:27-45` — existing integration test pattern: create textbook, create job, mock LLM, run build
  - `backend/tests/test_knowledge_graph_builder.py:18-28` — `_seed_textbook_and_chapter` helper

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/test_enrichment_integration.py -v` → PASS
  - [ ] At least one node has `equation_components` after build
  - [ ] `linked_node_id` values reference actual node IDs
  - [ ] Job status is "completed" with progress 1.0

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Full pipeline — graph build produces enriched nodes
    Tool: Bash (pytest)
    Preconditions: Mock ai_router with 2 responses: key result extraction (returns equation concept with defining_equation), enrichment (returns 3 components)
    Steps:
      1. Build graph for a test textbook
      2. Query all concept nodes
      3. Find node with defining_equation in metadata
      4. Assert that node also has equation_components in metadata
      5. Assert equation_components has 3 items
      6. Assert at least one component has linked_node_id pointing to a real node ID
    Expected Result: End-to-end enrichment works in the full build pipeline
    Evidence: .sisyphus/evidence/task-7-integration.txt

  Scenario: Edge case — graph with no equations still builds successfully
    Tool: Bash (pytest)
    Preconditions: Mock ai_router returns concept groups with NO defining_equations
    Steps:
      1. Build graph
      2. Assert job status is "completed"
      3. Assert no nodes have equation_components in metadata (enrichment was a no-op)
    Expected Result: Build succeeds, enrichment skipped gracefully
    Evidence: .sisyphus/evidence/task-7-no-equations.txt
  ```

  **Commit**: YES
  - Message: `test(graph): add equation enrichment integration tests`
  - Files: `backend/tests/test_enrichment_integration.py`
  - Pre-commit: `pytest backend/tests/test_enrichment_integration.py -v`

- [x] 8. End-to-End QA: Full stack verification

  **What to do**:
  - Start the backend and frontend
  - Generate a knowledge graph for a textbook that contains equations (e.g., the Shigley's textbook already in the data directory)
  - Click on equation nodes and verify the breakdown section appears
  - Verify calculated variables are clickable and navigate to their target node
  - Verify constants show descriptions and page references
  - Verify nodes without enrichment data show existing behavior (no empty sections)
  - Screenshot all evidence
  - Run the full test suite one final time

  **Must NOT do**:
  - DO NOT fix bugs in this task — report them for separate fixes
  - DO NOT modify code — this is verification only

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`playwright`]
    - Browser-based verification of the full feature

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 6, 7

  **References**:

  **Pattern References**:
  - `frontend/src/pages/GraphPage.tsx` — the page where the graph renders
  - `backend/app/routers/knowledge_graph.py` — API endpoints for graph data

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/ -v --tb=short` → all pass
  - [ ] `npx vitest run --reporter=verbose` → all pass
  - [ ] Screenshot: equation node clicked → breakdown section visible
  - [ ] Screenshot: calculated variable clicked → panel shows new node
  - [ ] Screenshot: non-enriched node → no breakdown section

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Full E2E — equation breakdown visible and interactive
    Tool: Playwright (browser)
    Preconditions: Backend running on localhost:8000, frontend on localhost:5173, graph generated for a textbook
    Steps:
      1. Navigate to http://localhost:5173
      2. Click on a textbook card to open it
      3. Navigate to the knowledge graph page
      4. Wait for graph to render (nodes visible)
      5. Click on a node that is an equation type
      6. Wait for ConceptDetailPanel to load
      7. Assert "Equation Breakdown" heading is visible in the panel
      8. Assert at least one variable item is listed
      9. Screenshot the panel showing the breakdown
      10. If a calculated variable exists, click it
      11. Assert panel updates to show the linked node's details
      12. Screenshot the updated panel
    Expected Result: Full interactive equation breakdown working end-to-end
    Failure Indicators: "Equation Breakdown" heading not found, no variable items rendered, click doesn't navigate
    Evidence: .sisyphus/evidence/task-8-e2e-breakdown.png, .sisyphus/evidence/task-8-e2e-navigation.png

  Scenario: Non-enriched node shows no breakdown
    Tool: Playwright (browser)
    Preconditions: Same as above
    Steps:
      1. Click on a chapter-level or section-level node (not an equation)
      2. Wait for ConceptDetailPanel to load
      3. Assert "Equation Breakdown" heading is NOT visible
    Expected Result: No breakdown section for non-equation nodes
    Evidence: .sisyphus/evidence/task-8-no-breakdown.png
  ```

  **Commit**: NO (verification only)

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest backend/tests/ -v` + `npx vitest run`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill)
  Start the app. Navigate to a textbook's knowledge graph. Click an equation node that has enrichment. Verify: breakdown section visible, calculated variables clickable, constants show description. Click a node without enrichment — verify no breakdown section appears. Screenshot evidence.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built, nothing beyond spec. Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| # | Message | Files | Pre-commit |
|---|---------|-------|------------|
| 1 | `feat(storage): add update_concept_node_metadata method` | `storage.py`, `test_storage_update.py` | `pytest backend/tests/test_storage_update.py -v` |
| 2 | `feat(prompts): add equation enrichment prompt and parser` | `knowledge_graph_prompts.py`, `test_equation_enrichment_prompts.py` | `pytest backend/tests/test_equation_enrichment_prompts.py -v` |
| 3 | `feat(graph): wire equation enrichment into build pipeline` | `knowledge_graph_builder.py`, `test_equation_enrichment.py` | `pytest backend/tests/test_equation_enrichment.py -v` |
| 4 | `feat(ui): add equation breakdown section to ConceptDetailPanel` | `ConceptDetailPanel.tsx`, `ConceptDetailPanel.test.tsx`, `graph.css` | `npx vitest run src/components/graph/ConceptDetailPanel.test.tsx` |

---

## Success Criteria

### Verification Commands
```bash
pytest backend/tests/ -v --tb=short       # Expected: all pass, 0 failures
npx vitest run --reporter=verbose          # Expected: all pass, 0 failures
```

### Final Checklist
- [ ] All "Must Have" items implemented and verified
- [ ] All "Must NOT Have" items verified absent
- [ ] All tests pass (backend + frontend)
- [ ] Enrichment runs automatically during graph build
- [ ] ConceptDetailPanel shows equation breakdown for enriched nodes
- [ ] Calculated variables are clickable and navigate to their node
- [ ] Constants show description + page reference
- [ ] Nodes without enrichment show existing behavior unchanged
