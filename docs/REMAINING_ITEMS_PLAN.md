# Remaining Items Plan: zena-deep-research → zena-workflow-spike

**Created:** December 17, 2025
**Status:** ✅ Complete (repository can be deleted)
**Related:** `INTEGRATION_PLAN.md`

---

## Overview

This document tracked high-value items from `zena-deep-research` that needed to be ported to `zena-workflow-spike`.

**Status:** All critical items have been ported. This repository can be safely deleted.

---

## Porting Status

| Item | Status | Location in zena-workflow-spike |
|------|--------|--------------------------------|
| **1. Token Limit Handling** | ✅ Complete | `zena/shared/utilsv2.py` |
| **2. Vector Store Embedding** | ✅ Complete | `zena/database/operations/research.py` |
| **3. Additional Prompts** | ✅ Complete | `zena/workflows/research_workflow/prompts/` (Langfuse) |
| **4. Document Ingestion** | ✅ Complete | `zena/agents/document_ingester_v2/` |
| **5. Chunking Utilities** | ✅ Complete | `zena/agents/document_ingester_v2/docling_processor.py` |
| **6. Configuration Pattern** | ✅ Complete | `zena/shared/langsmith.py` |
| **7. Evaluation Framework** | ⏳ Future | Not ported (see note below) |

---

## Future: Evaluation Framework

**Status:** Deferred - will use Langfuse instead

The custom evaluation framework (`tests/evaluators.py`, `tests/prompts.py`, `tests/run_evaluate.py`) was not ported because:

1. **Langfuse has built-in evaluation** - We'll use Langfuse's evaluation features for quality monitoring
2. **Low priority** - Core workflows work without it
3. **Post-launch concern** - Can be implemented when we need systematic v1 vs v2 comparisons

If needed in the future, the evaluation concepts (LLM-as-judge for depth, rigor, relevance, writing quality) can be implemented using Langfuse's evaluation API.

---

## Conclusion

**This repository can be safely deleted.** All production-critical functionality has been ported to `zena-workflow-spike`.
