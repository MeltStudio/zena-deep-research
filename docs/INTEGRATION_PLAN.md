# Integration Plan: zena-deep-research into zena-workflow-spike

## Status: ✅ COMPLETE (December 23, 2025)

All integration work is complete. This document is kept for historical reference.

---

## Completed Work

| Phase | Description | Status | Reference |
|-------|-------------|--------|-----------|
| Phase 1 | Document Ingestion v2 (Docling) | ✅ Complete | PR #64 |
| Phase 2 | LangGraph Workflow Integration | ✅ Complete | PR #76 |
| Phase 3 | v2 Workflows (Strategic Plan v2, Report Gen v3) | ✅ Complete | PR #76 |
| Database Split | Python/Next.js separate databases | ✅ Complete | - |
| Workflow Cleanup | Remove v1 code, keep only latest versions | ✅ Complete | Commit `1ceabf7` |
| Frontend Integration | conclusions, bibliography, report_structure | ✅ Complete | - |
| Research v2 | Now the only research workflow | ✅ Complete | - |

---

## Final Architecture

### Workflows in Production

| Workflow | File | Description |
|----------|------|-------------|
| Research | `research_workflow/graphv2.py` | Supervisor/researcher pattern with web search |
| Strategic Planning | `strategic_planning_workflow/graphv2.py` | Text-based report plan |
| Report Generation | `report_generation_workflow/graphv3.py` | Section sketches, conclusions, bibliography |

### Key Design Decisions

| Decision | Choice |
|----------|--------|
| Section sketches | Internal to report generation (not exposed to users) |
| Feature flags | None - v2 is the only version |
| API changes | Added `conclusions`, `bibliography`, `report_structure` to GeneratedReport |
| Prompts | Managed in Langfuse |
| Observability | `@observe()` decorators on all nodes |

---

## Future Considerations

These items are out of scope for this integration but may be addressed later:

- **Reprocessing**: Batch job to reprocess v1 documents with v2 Docling pipeline
- **MCP Integration**: Model Context Protocol servers for extended capabilities
- **Report Templates**: Customizable report formats
- **Report Versioning**: Version history and approval/rejection flow
- **Per-Section Feedback**: Section-level regeneration
