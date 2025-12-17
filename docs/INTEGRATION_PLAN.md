# Integration Plan: v2 Workflows

## Overview

Upgrade zena-workflow-spike workflows to v2 by merging the best of both zena-workflow-spike and zena-deep-research implementations.

## Cross-Cutting Requirements

| Requirement | Notes |
|-------------|-------|
| **Langfuse Observability** | All workflow nodes must have `@observe()` decorator for tracing. This is already implemented across existing workflows - v2 must maintain this pattern. |
| **LangSmith/LangGraph Studio Development** | All workflows must be runnable from LangSmith/LangGraph Studio for development and debugging. Follow existing `langgraph.json` configuration pattern. Individual workflows exposed separately, plus a combined "full pipeline" graph that chains all workflows. Nodes must use `Configuration` class with `config_schema` parameter for LangGraph Studio UI configuration. |
| **Supervisor Pattern** | Follow the same supervisor/researcher architecture used in `research_workflow_v2`. Supervisor delegates tasks, researchers execute with tools. |
| **Tool Access by Workflow Stage** | **research_workflow**: web search (Tavily) + internal docs. **strategic_plan & report_generation**: only `search_research_findings` (PR #72) - no new web searches. Downstream workflows synthesize from existing research, not conduct new searches. |

## Current Status

| Workflow | Status | Notes |
|----------|--------|-------|
| `research_workflow_v2` | ✅ Complete | PR #71 merged, PR #72 merged |
| `restatement_workflow_v2` | ✅ Design Complete | No v2 needed - current implementation sufficient. Decisions documented. |
| `strategic_plan_workflow_v2` | ✅ Design Complete | All decisions made. Ready for implementation. |
| `report_generation_workflow_v2` | ✅ Design Complete | All decisions made. Ready for implementation. |

---

## Completed: research_workflow_v2

### Tasks

- [x] **Vector search over findings** - PR #72 merged
- [ ] **Test end-to-end with real data** (pending)

### PR #72: Vector Search Methods (MERGED)

Adds database operations for searching research data:
- `search_research_findings()` - Vector search on findings by report_id
- `search_research_sources()` - Vector search on sources by research_session_id
- `search_hybrid_research()` - Hierarchical search (findings first, then sources)

**Usage in downstream workflows:**
- **strategic_plan_workflow_v2**: Use `search_research_findings()` in `analyze_research` node to retrieve relevant findings for hypothesis generation
- **report_generation_workflow_v2**: Use `search_hybrid_research()` in `section_researcher` to get relevant research per section

---

## restatement_workflow_v2 Review

### Current Implementation (spike)

**Architecture:** 6-node workflow

```
collect_project_context → search_global_context → generate_restatement →
save_draft_restatement → [webhook: END | CLI: request_approval → save_restatement]
```

**Strengths:**
- Rich context collection (client profile, company, project requirements, strategic questions)
- Global context search (definitions, analyses, formulas)
- Document search with iterative refinement
- Approval/rejection flow with feedback loop
- Database persistence with embeddings
- Webhook mode for API integration

**Weaknesses:**
- No validation of required fields before LLM call
- Possible orphaned draft records

### Decisions Made

| Question | Decision | Notes |
|----------|----------|-------|
| Add clarification step? | **No** | Form input is already structured; clarification not needed |
| Persist context sources? | **No** | Current metadata summary is sufficient |

---

## strategic_plan_workflow_v2 Design

### Comparison: Current Implementations

#### zena-workflow-spike (Current v1)

**Architecture:** 8-node workflow focused on strategic narrative

```
load_context → analyze_research → generate_strategic_hypothesis →
establish_recommendations → plan_argumentative_flow → structure_report_plan →
validate_plan → persist_plan
```

**Strengths:**
- Rich strategic artifacts (hypothesis, recommendations framework, argumentative flow)
- Validation step with quality scoring
- User approval/rejection flow with feedback loop
- Celery integration + API endpoints
- Langfuse prompt management
- Database persistence with revision tracking

**Weaknesses:**
- Report structure is template-based (not research-driven)
- No section-level planning (just section names/descriptions)
- No "section sketches" - jumps straight to report generation
- Doesn't determine research depth per section

#### zena-deep-research (LangGraph)

**Architecture:** Multi-stage report planning with section-level research

```
write_report_plan → report_supervisor → [parallel report_researchers] →
compress_report_research → write_report_section → final_report_generation
```

**Strengths:**
- Detailed per-section research requirements (depth levels: Deep Dive/Moderate/Surface)
- "Derives From" dependencies to avoid redundant research
- Section sketches with inline citations
- Parallel section research execution
- Resource optimization (surface sections reuse deep dive findings)

**Weaknesses:**
- No strategic hypothesis or recommendations framework
- No validation step
- No user approval flow
- Hardcoded report structure (should be dynamic from `report_types.json`)
- No database persistence layer
- No Celery/API integration

### Proposed v2 Architecture

Merge strategic depth from spike with section-level planning from deep-research.

```
Phase 1: Strategic Foundation (from spike)
├── load_context
├── analyze_research
│   ├── Invokes supervisor/researcher subgraph
│   ├── Researchers use PR #72 search_research_findings
│   ├── OUTPUT MUST BE COMPREHENSIVE - feeds all downstream nodes
│   ├── Use configurable model (default to high-quality model, not Haiku)
│   └── Produces rich findings for: hypothesis, recommendations, section planning, sketches
├── generate_strategic_hypothesis (uses PR #72 to query findings from analyze_research)
└── establish_recommendations

Phase 2: Section-Level Planning (NEW)
├── plan_argumentative_flow (separate node - kept from v1)
│   └── Output: argumentative_flow (used as prompt input for downstream nodes)
├── plan_report_sections
│   ├── Load suggested outline from report_types.json
│   ├── LLM can add/remove/modify sections based on research
│   ├── Assign depth levels per section (Deep Dive/Moderate/Surface)
│   └── Output: final section structure for sketch generation
└── generate_section_sketches (supervisor assigns sections to researchers)
    ├── Supervisor assigns CONTENT sections by depth level:
    │   ├── Deep Dive: 1 section/researcher
    │   ├── Moderate: up to 2 sections/researcher
    │   └── Surface-level: up to 3 sections/researcher
    ├── Uses PR #72 search + analyze_research output + argumentative_flow
    ├── Creates outline/sketch per CONTENT section
    └── Includes citation placeholders

Phase 3: Validation & Approval (from spike)
├── validate_plan (enhanced with section coverage check)
├── persist_draft_plan
├── request_approval (user reviews plan + section sketches)
│   ├── If approved → persist_plan (final)
│   └── If rejected → regenerate with feedback (loop back to relevant phase)
└── persist_plan
```

### Implementation Notes

**analyze_research improvements needed:**
- Current summary is too condensed - needs to be more complete
- Downstream prompts only use limited insights - should use more
- Currently uses Haiku model (mediocre results) - need configurable model defaulting to higher quality
- Follow PR #74's `StrategicPlanningConfiguration` pattern for model config

**Supervisor pattern:**
- `analyze_research`: Create new supervisor using same structure as `research_workflow_v2`, but with prompts aligned to strategic analysis goal (not general research). Tools: PR #72 search only.
- `generate_section_sketches`: Supervisor assigns CONTENT sections to researchers based on depth level:
  - Deep Dive: 1 section per researcher (full research)
  - Moderate: up to 2 sections per researcher (standard research)
  - Surface-level: up to 3 sections per researcher (minimal research, derives from other sections)
  - Parallel execution with configurable concurrency (default 8)

**PR #72 tool integration (MERGED):**
- Create LangChain tools wrapping PR #72 database operations:
  - `search_research_findings_tool` - wraps `search_research_findings()`
  - `search_research_sources_tool` - wraps `search_research_sources()`
  - `search_hybrid_research_tool` - wraps `search_hybrid_research()`
- Wire these tools into the strategic planning supervisor/researchers

**report_types.json integration:**
- Add `suggested_outline` field to `report_types.json` schema and parser
- Migrate existing outlines from `report_templates.py` (will be removed):
  - Competitive Deep Dive, Market Trends, Consumer Insights, Brand Positioning, Product Brain Stormer, Default
- Team will provide content for any missing report types
- For initial implementation, can generate placeholder outlines for types not yet defined

### Decisions Made

| Question | Decision | Notes |
|----------|----------|-------|
| Section sketches location? | **A) In strategic plan** | User can review/approve sketches before report generation |
| Keep argumentative_flow separate? | **A) Keep both** | Maintain as separate field; use as prompt input during section generation |
| Report structure source? | **`report_types.json`** | Each report type defines suggested sections; strategic plan can add/remove sections based on analysis |

### Decisions Made (continued)

| Question | Decision | Notes |
|----------|----------|-------|
| Template customization? | **C) Hybrid** | `report_types.json` provides suggested outline per report type; LLM can add/remove sections and adjust section depth based on analysis |

---

## report_generation_workflow_v2 Design

### Comparison: Current Implementations

#### zena-workflow-spike (Current v1)

**Architecture:** 13-node workflow with validation/refinement loops

```
load_context → gather_data → structure_report → generate_sections →
[Production: validate_report → retrieve_additional_info → check_consistency → refine_report (loop)] →
finalize_report → create_executive_summary → add_cover → regulatory_review → save_file
```

**Strengths:**
- Rich data aggregation (research, documents, internal context, client questions, dynamic fields)
- Strategic plan integration (hypothesis, recommendations, argumentative flow passed to section generation)
- Quality validation with consistency checking
- Optional refinement loop based on validation scores
- Report templates (6 types: Competitive Deep Dive, Market Trends, Consumer Insights, etc.)
- Executive summary, cover page, regulatory review as separate steps
- Markdown formatter with TOC generation
- Database persistence with embeddings
- S3 upload support
- Celery integration with retries
- Test mode vs production mode

**Weaknesses:**
- Generates all sections in single LLM call (no per-section research)
- No section sketches - goes straight from plan to final content
- No "Derives From" dependency awareness
- No per-section depth levels
- Refinement loop is **broken** (critical issue - needs fix in v2)

#### zena-deep-research (LangGraph)

**Architecture:** Section-by-section research with parallel execution

```
write_report_plan → report_supervisor → [parallel report_researchers per section] →
compress_report_research → write_report_section → final_report_generation
```

**Strengths:**
- Per-section research with depth levels (Deep Dive/Moderate/Surface)
- "Derives From" dependencies - surface sections synthesize from deep sections
- Section sketches with inline citations before final assembly
- Parallel section execution (up to 8 concurrent)
- Citation utilities (extraction, parsing, renumbering)
- Progressive token limit handling with truncation

**Weaknesses:**
- No strategic hypothesis or recommendations framework
- No validation or consistency checking
- No refinement loop
- No data aggregation from multiple sources (just search results)
- No executive summary/cover page as separate steps
- No database persistence
- No Celery/API integration
- Citation renumbering relies on model (not explicit)

### Proposed v2 Architecture

Full merge of best parts from both implementations.

```
Phase 1: Context Loading (from spike)
├── load_context (strategic plan with section_plan, research, restatement)
└── gather_data (documents, internal context, client questions, dynamic fields)

Phase 2: Section-Level Generation (from deep-research, enhanced)
├── Supervisor assigns sections to researchers based on depth level:
│   ├── Deep Dive: 1 section per researcher (full research)
│   ├── Moderate: up to 2 sections per researcher (standard research)
│   └── Surface-level: up to 3 sections per researcher (minimal research)
│
├── For each content section in section_plan (from strategic_plan_v2):
│   ├── Uses approved section_sketch from strategic_plan as starting point
│   ├── Depth level determines research intensity and researcher assignment
│   ├── "Derives From" sections wait for dependencies, then synthesize
│   └── Parallel execution (configurable concurrency, default 8)
│
├── section_researcher (assigned by supervisor)
│   ├── USE PR #72: search_hybrid_research() for relevant findings + sources
│   ├── Filter relevant internal docs/context
│   └── Output: section research bundle (additional context for expansion)
│
├── expand_section (per section)
│   ├── INPUT: approved section_sketch from strategic_plan
│   ├── Expands sketch into full prose using research bundle + strategic context
│   ├── Maintains inline citations from sketch, adds new citations as needed
│   └── Output: full section content with sources
│
├── Collect all expanded sections
│
└── NOTE: Standard sections (Executive Summary, Conclusions, Bibliography, TOC, Cover)
    are NOT part of Phase 2 - they are generated in Phase 4 after content is complete

Phase 3: Assembly & Validation (from spike, enhanced)
├── assemble_draft_report (combine expanded sections with citation renumbering)
├── validate_report (quality + consistency + citation coverage)
├── [conditional] retrieve_additional_info (fill gaps - USE PR #72 for targeted search)
├── [conditional] refine_sections (targeted per-section refinement)
└── finalize_report

Phase 4: Standard Sections & Persist (from spike)
├── create_executive_summary (synthesizes all content sections)
├── create_conclusions (synthesizes key findings)
├── generate_bibliography (citation utility extracts all sources)
├── generate_table_of_contents (from final structure)
├── add_cover_page
├── regulatory_review (if applicable)
└── save_report (DB + S3)
```

### What We Take From Each

| From Spike | From Deep Research |
|------------|-------------------|
| Rich data aggregation (docs, context, questions) | Per-section research with depth levels |
| Strategic plan integration (hypothesis, recommendations) | "Derives From" dependency handling |
| Validation + consistency checking | Parallel section execution |
| Refinement loop (targeted, not full) | Citation utilities (extraction, parsing, renumbering) |
| Executive summary, cover, regulatory review | Progressive token limit handling |
| Report templates | |
| Database persistence + S3 | |
| Celery integration | |
| User approval with version history | |

### Key Distinction: Content Sections vs Standard Sections

**Content sections** are the unique, research-driven sections that vary by report type (e.g., Market Analysis, Competitive Landscape, Consumer Insights). These:
- Are defined in `section_plan` from `strategic_plan_workflow_v2`
- Have depth levels (Deep Dive / Moderate / Surface-level) that determine research intensity
- Can have `derives_from[]` dependencies on other content sections
- Get sketches created and approved in strategic_plan
- Are expanded into full prose in report_generation Phase 2

**Standard sections** are generated automatically for every report and don't need planning or sketches:
- Executive Summary (synthesizes all content sections)
- Conclusions (synthesizes key findings)
- Bibliography (generated by citation utility)
- Table of Contents (generated from final structure)
- Cover Page

Standard sections are generated in Phase 4, AFTER all content sections are complete, because they need the full report context.

### Key Distinction: Sketches vs Expansion

**Section sketches** are created in `strategic_plan_workflow_v2` and approved by the user before report generation begins. This allows users to review the planned content and structure before investing in full prose generation.

**Section expansion** happens in `report_generation_workflow_v2`. It takes the approved sketches and expands them into full prose, adding additional research context and citations as needed. This is NOT creating new sketches - it's expanding approved outlines into final content.

### Decisions Made

| Question | Decision | Notes |
|----------|----------|-------|
| Section research: new searches or retrieve existing? | **A) Vector search only** | No new Tavily searches - use PR #72 to retrieve from existing research_findings/sources. See Cross-Cutting Requirements. |

### Decisions Made (continued)

| Question | Decision | Notes |
|----------|----------|-------|
| Citation renumbering approach? | **A) Explicit utility** | LLM injects URLs/sources directly in markdown; utility extracts sources, generates bibliography section, and replaces inline refs with numbered citations [1], [2], etc. Deterministic and reliable. |
| Parallel execution limit? | **Fixed at 8, configurable** | Default to 8 concurrent section researchers; parameter comes from config for easy future adjustment |
| Refinement scope? | **Per-section + consistency loop** | Regenerate problematic section(s), then run consistency check across all sections. If inconsistencies found, regenerate affected sections. Supports both per-section and report-level user feedback. |
| Where to store section sketches? | **StrategicPlan table** | Store alongside existing `report_structure` field (proposed outline). User can see both outline and sketches when reviewing strategic plan. |
| Should "Derives From" content sections skip research? | **A) Yes - synthesize only** | Content sections with `derives_from[]` dependencies synthesize from their referenced sections. No additional research - just synthesize. (Note: Standard sections like Executive Summary and Conclusions are separate - they're generated in Phase 4 from the full report.) |
| User approval for final report? | **Yes - with version history** | User can give feedback on individual sections and/or the full report. Feedback triggers targeted regeneration. Upon approval, report is marked as "final" which triggers downstream outputs (PowerPoint, PDF). Post-approval modifications create new versions (v2, v3, etc.) with full version history. Each version can be approved to regenerate outputs. |

---

## Workflow Interfaces Review

Each workflow produces artifacts consumed by the next. We need to ensure optimal data flow.

### v2 Artifact Flow

```
restatement_workflow
    │
    ├── Consumes: Intake form data (client profile, company, project requirements, strategic questions)
    ├── Produces: ProblemRestatement (text, objectives, constraints, context_summary)
    ├── Produces: Shared ReportContext object (initialized with restatement + intake data)
    │
    ▼
research_workflow_v2
    │
    ├── Consumes: ReportContext (restatement_text + raw intake data)
    ├── Consumes: [Feature flag] global_context (definitions, analyses, formulas)
    ├── Produces: ResearchSession (summary, key_insights)
    │   └── Note: contradictions/coverage_gaps resolved by supervisor; surfaced to user if unresolved
    ├── Produces: ResearchFindings (compressed summaries with embeddings) - queryable via PR #72
    ├── Produces: ResearchSources (individual sources with embeddings) - queryable via PR #72
    ├── Updates: ReportContext with research_session_id
    │
    ▼
strategic_plan_workflow_v2
    │
    ├── Consumes: ReportContext (restatement, intake data, research_session_id)
    ├── Queries: ResearchFindings dynamically via PR #72 vector search
    ├── Produces: StrategicPlan
    │   ├── hypothesis (strategic hypothesis)
    │   ├── recommendations_framework
    │   ├── argumentative_flow (separate field, used as prompt input)
    │   ├── section_plan (CONTENT sections only - NOT exec summary, conclusions, etc.)
    │   │   └── Each section has: name, description, depth_level, derives_from[]
    │   └── section_sketches (outline per CONTENT section with citation placeholders)
    ├── User approval: Reviews plan + sketches before proceeding
    ├── Updates: ReportContext with strategic_plan_id
    │
    ├── NOTE: Standard sections are NOT in section_plan:
    │   └── Executive Summary, Conclusions, Bibliography, TOC, Cover Page
    │       → These are generated in report_generation Phase 4
    │
    ▼
report_generation_workflow_v2
    │
    ├── Consumes: ReportContext (restatement, intake questions, strategic_plan with sketches)
    │
    ├── Phase 2: Content Section Generation
    │   ├── Supervisor assigns CONTENT sections to researchers by depth level
    │   │   ├── Deep Dive: 1 section/researcher
    │   │   ├── Moderate: up to 2 sections/researcher
    │   │   └── Surface-level: up to 3 sections/researcher
    │   ├── Queries: ResearchFindings/Sources via PR #72 for section expansion
    │   ├── Expands: Approved section_sketches → full prose (parallel, max 8 concurrent)
    │   └── "Derives From" content sections wait for dependencies, then synthesize
    │
    ├── Phase 3: Assembly & Validation
    │   ├── Assemble expanded content sections with citation renumbering
    │   ├── Validate: Per-section + consistency loop
    │   └── User feedback: Per-section and/or full report feedback → targeted regeneration
    │
    ├── Phase 4: Standard Sections (generated AFTER content is complete)
    │   ├── Executive Summary (synthesizes all content sections)
    │   ├── Conclusions (synthesizes key findings)
    │   ├── Bibliography (generated by citation utility from all sources)
    │   ├── Table of Contents (generated from final structure)
    │   └── Cover Page
    │
    ├── Produces: GeneratedReport
    │   ├── markdown (full report with TOC)
    │   ├── sections[] (individual section content)
    │   ├── executive_summary
    │   ├── conclusions
    │   ├── bibliography
    │   ├── version (v1, v2, v3...)
    │   └── status (draft/approved)
    │
    ├── User approval: Marks report as "final"
    │   └── Triggers: PowerPoint generation, PDF export, other outputs
    ├── Post-approval changes: Create new version (v2, v3...) with full history
    │
    ▼
END (with version history preserved)
```

### Shared ReportContext Object

A single context object passed through all workflows containing latest/approved versions:

```python
class ReportContext:
    # From restatement_workflow
    problem_restatement: ProblemRestatement
    intake_data: dict  # Raw intake form data for reference

    # From research_workflow_v2
    research_session_id: str  # For PR #72 queries

    # From strategic_plan_workflow_v2
    strategic_plan_id: str

    # Metadata
    report_id: str
    workspace_id: str
    current_version: int
```

### Questions to Review

| Interface | Question | Notes |
|-----------|----------|-------|
| **Restatement → Research** | ~~Is `restatement_text` sufficient?~~ | **DECIDED**: Pass both `restatement_text` AND raw intake data. Prompt should clarify that restatement is the refined/approved version, while intake is raw data for reference if needed. |
| **Restatement → Research** | ~~Should `global_context` be passed?~~ | **DECIDED**: Feature flag (default disabled). Allows A/B testing to measure if global_context improves report quality. Can enable later if valuable. |
| **Research → Strategic Plan** | ~~Is `ResearchSession.key_insights` enough?~~ | **DECIDED**: Query `ResearchFindings` dynamically via PR #72 vector search based on what information is needed in each step |
| **Research → Strategic Plan** | ~~Are `contradictions` and `coverage_gaps` needed?~~ | **DECIDED**: Supervisor should resolve these through iteration. If they persist after max iterations, surface to user for resolution (upload more docs, provide clarification, or choose interpretation). |
| **Strategic Plan → Report** | ~~Is `section_plan` (v2) sufficient?~~ | **DECIDED**: `section_plan` is needed, but report generation also needs access to `problem_restatement` and intake form questions (what user wants answered). |
| **Strategic Plan → Report** | ~~Should `recommendations_framework` map explicitly to sections?~~ | **DECIDED**: No - keep implicit. Don't constrain the LLM; it may decide to use a recommendation in a different section than expected. |
| **All → All** | ~~Should we have a shared "report context" object?~~ | **DECIDED**: Yes - create shared context object passed through all workflows. Must always contain latest/approved versions of restatement, strategic plan, etc. Handle versioning carefully. |

### Validation Issues to Fix

**Current `report_validator.py` problems:**
1. **Truncates to 10k chars** (line 168) - misses most of the report content
2. **Uses Haiku model** (`ModelPreset.BALANCED`) - not thorough enough for validation
3. **Defaults to 0.8 score on error** (line 143) - masks validation failures

**v2 fixes needed:**
- Validate full report (or validate per-section, then aggregate)
- Use higher-quality model for validation (configurable)
- Fail properly on validation errors instead of passing silently

### Scoring Configuration Review

**Issue:** Scores throughout the application are hardcoded arbitrary numbers from initial development. Need to:
- Move all score thresholds to configuration
- Re-evaluate what scores actually mean and their appropriate thresholds
- Make scoring criteria consistent across workflows

**Areas to review:**
- Validation scores (completeness, consistency, evidence, quality)
- Similarity thresholds for vector search
- Quality thresholds for refinement triggers
- Any other hardcoded score comparisons

---

## Future Considerations

- **Reprocessing**: Batch job to reprocess v1 documents with v2 Docling pipeline
- **MCP Integration**: Model Context Protocol servers for extended capabilities
- **Report Templates**: Customizable report formats
- **A/B Testing**: Compare v1 vs v2 output quality
