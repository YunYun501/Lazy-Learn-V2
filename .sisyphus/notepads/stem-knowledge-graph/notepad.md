
## Task: Allow Graph Generation from Partially Extracted Textbooks

**Completed**: 2026-03-16

### Changes Made

1. **Backend Router Guard** (`knowledge_graph.py` line 60-64)
   - Changed from requiring `pipeline_status == "fully_extracted"`
   - Now allows: `partially_extracted`, `extracting`, `fully_extracted`
   - Error message updated to reflect partial extraction support

2. **Graph Builder Filter** (`knowledge_graph_builder.py` line 22-26)
   - Added filtering: only processes chapters with `extraction_status == "extracted"`
   - Gracefully handles case where no extracted chapters exist
   - Returns early with failed status if no chapters to process

3. **Frontend Button** (`CoursePreviewView.tsx` line 116)
   - Updated disabled state to check for allowed statuses
   - Button now enabled for `partially_extracted` and `extracting` states

4. **Test Updates** (`test_knowledge_graph_router.py`)
   - Renamed: `test_build_endpoint_rejects_not_fully_extracted` → `test_build_endpoint_rejects_uploaded_status`
   - Added: `test_build_endpoint_allows_partially_extracted` (verifies 202 response)
   - Fixed test helper: chapters now marked as `extraction_status='extracted'`

### Test Results
- ✅ 16/16 backend tests pass (11 router + 5 builder)
- ✅ Frontend TypeScript: 0 errors
- ✅ All expected outcomes met

### Key Behavior
- Graph can now be generated when pipeline has ANY extracted chapters
- Builder skips pending/deferred/error chapters automatically
- Frontend button reflects actual capability (not just fully_extracted)
