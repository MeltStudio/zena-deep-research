# Integration Plan: v2 Workflows

## Overview

Upgrade zena-workflow-spike workflows to v2 by merging the best of both zena-workflow-spike and zena-deep-research implementations.

## Cross-Cutting Requirements

| Requirement | Notes |
|-------------|-------|
| **Langfuse Observability** | All workflow nodes must have `@observe()` decorator for tracing. This is already implemented across existing workflows - v2 must maintain this pattern. |

## Current Status

| Workflow | Status | Notes |
|----------|--------|-------|
| `research_workflow_v2` | ✅ Complete | PR #71 merged, PR #72 pending |
| `restatement_workflow_v2` | 📋 Review Needed | Assess improvements from deep-research |
| `strategic_plan_workflow_v2` | 📋 Planning | Design complete, questions to discuss |
| `report_generation_workflow_v2` | 📋 Planning | Design complete, questions to discuss |

---

## Active Work: research_workflow_v2

### Remaining Tasks

- [ ] **Vector search over findings** - PR #72 (draft, branch: `feature/research-vector-search-tool`)
- [ ] **Test end-to-end with real data**

### PR #72: Vector Search Methods

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
├── analyze_research (USE PR #72: search_research_findings for relevant research)
├── generate_strategic_hypothesis (USE PR #72: search_research_findings to retrieve relevant findings)
└── establish_recommendations

Phase 2: Section-Level Planning (NEW - from deep-research concepts)
├── plan_report_sections (replaces argumentative_flow + structure_report_plan)
│   ├── Assign depth levels per section (Deep Dive/Moderate/Surface)
│   ├── Identify "Derives From" dependencies
│   ├── Map recommendations to sections
│   └── Define required information per section
└── generate_section_sketches (OPTIONAL - parallel outlines per section)
    ├── Uses PR #72 search to retrieve relevant findings
    ├── Creates outline/sketch per section
    └── Includes citation placeholders

Phase 3: Validation & Persistence (from spike)
├── validate_plan (enhanced with section coverage check)
└── persist_plan
```

### Decisions Made

| Question | Decision | Notes |
|----------|----------|-------|
| Section sketches location? | **A) In strategic plan** | User can review/approve sketches before report generation |
| Keep argumentative_flow separate? | **A) Keep both** | Maintain as separate field; use as prompt input during section generation |
| Report structure source? | **`report_types.json`** | Each report type defines suggested sections; strategic plan can add/remove sections based on analysis |

### Questions to Discuss

| Question | Options | Notes |
|----------|---------|-------|
| **How much can strategic plan modify template sections?** | A) Only customize content within template sections<br>B) Can add sections but not remove<br>C) Full flexibility (add/remove based on analysis) | Manuel leans toward C - strategic plan should be able to adapt structure to specific markets or user questions |

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
├── For each section in section_plan (from strategic_plan_v2):
│   ├── Depth level determines research intensity
│   ├── "Derives From" sections use existing sketches (no new research)
│   └── Parallel execution (configurable concurrency)
│
├── section_researcher (per section)
│   ├── USE PR #72: search_hybrid_research() for relevant findings + sources
│   ├── Filter relevant internal docs/context
│   └── Output: section research bundle
│
├── write_section_sketch (per section)
│   ├── Uses strategic hypothesis + recommendations for this section
│   ├── Includes inline citations [1], [2]
│   └── Output: section_sketch with sources
│
└── Collect all section_sketches

Phase 3: Assembly & Validation (from spike, enhanced)
├── assemble_draft_report (combine sketches with citation renumbering)
├── validate_report (quality + consistency + citation coverage)
├── [conditional] retrieve_additional_info (fill gaps - USE PR #72 for targeted search)
├── [conditional] refine_sections (targeted per-section refinement)
└── finalize_report

Phase 4: Polish & Persist (from spike)
├── create_executive_summary
├── add_cover
├── regulatory_review (if applicable)
└── save_report (DB + S3)
```

### What We Take From Each

| From Spike | From Deep Research |
|------------|-------------------|
| Rich data aggregation (docs, context, questions) | Per-section research with depth levels |
| Strategic plan integration (hypothesis, recommendations) | "Derives From" dependency handling |
| Validation + consistency checking | Section sketches with inline citations |
| Refinement loop (targeted, not full) | Parallel section execution |
| Executive summary, cover, regulatory review | Citation utilities (extraction, parsing, renumbering) |
| Report templates | Progressive token limit handling |
| Database persistence + S3 | |
| Celery integration | |

### Questions to Discuss

| Question | Options | Notes |
|----------|---------|-------|
| **Section research: new searches or just retrieve existing?** | A) Vector search on existing research_findings/sources (PR #72)<br>B) New Tavily searches per section<br>C) Hybrid (retrieve first, search if gaps) | Option A reuses research_workflow_v2 output; B is more thorough but slower/costlier |
| **Citation renumbering approach** | A) Explicit utility (deterministic)<br>B) Let model handle it<br>C) Hybrid (utility + model cleanup) | Model-only has failed in testing; utility is more reliable |
| **Parallel execution limit** | A) Fixed (e.g., 4)<br>B) Configurable per report type<br>C) Dynamic based on section count | More parallelism = faster but higher resource usage |
| **Refinement scope** | A) Full report regeneration<br>B) Per-section targeted refinement<br>C) Only sections that failed validation | Per-section is more efficient but adds complexity |
| **Where to store section sketches?** | A) Only in-memory during workflow<br>B) Persist in generated_reports table<br>C) Separate table | Persisting helps debugging and potential reuse |
| **Should "Derives From" sections skip research entirely?** | A) Yes - synthesize only from referenced sections<br>B) No - still do light research<br>C) Configurable per section | Skipping saves cost but may miss nuances |

---

## Workflow Interfaces Review

Each workflow produces artifacts consumed by the next. We need to ensure optimal data flow.

### Current Artifact Flow

```
restatement_workflow
    │
    ├── Produces: ProblemRestatement (text, objectives, constraints, context_summary)
    │
    ▼
research_workflow_v2
    │
    ├── Consumes: ProblemRestatement
    ├── Produces: ResearchSession (summary, key_insights, contradictions, coverage_gaps)
    ├── Produces: ResearchFindings (compressed summaries with embeddings)
    ├── Produces: ResearchSources (individual sources with embeddings)
    │
    ▼
strategic_plan_workflow
    │
    ├── Consumes: ProblemRestatement, ResearchSession
    ├── Produces: StrategicPlan (hypothesis, recommendations, argumentative_flow, report_structure)
    │
    ▼
report_generation_workflow
    │
    ├── Consumes: ProblemRestatement, ResearchSession, StrategicPlan
    ├── Produces: GeneratedReport (markdown, sections, executive_summary)
    │
    ▼
END
```

### Questions to Review

| Interface | Question | Notes |
|-----------|----------|-------|
| **Restatement → Research** | Is `restatement_text` sufficient to guide research? | Research brief is generated from this field; `objectives`, `constraints`, `context_summary` also available |
| **Restatement → Research** | Should `restatement_text` be enhanced? | Francisco suggests a richer summary; current text may be missing key context |
| **Restatement → Research** | Should intake form be passed to research? | Research may benefit from seeing raw user questions directly, not just the restatement |
| **Restatement → Research** | Should `global_context` be passed or scrapped entirely? | **⚠️ TEAM DISCUSSION NEEDED**: Francisco says not needed; Sebastián built this functionality. Need alignment on whether to keep, modify, or remove |
| **Research → Strategic Plan** | ~~Is `ResearchSession.key_insights` enough?~~ | **DECIDED**: Query `ResearchFindings` dynamically via PR #72 vector search based on what information is needed in each step |
| **Research → Strategic Plan** | Are `contradictions` and `coverage_gaps` being used? | Francisco says not needed; Manuel sees potential for user-facing conflict resolution. Keep open for debate |
| **Strategic Plan → Report** | Is `section_plan` (v2) sufficient for section-level generation? | New artifact; needs to include all context per section |
| **Strategic Plan → Report** | Should `recommendations_framework` map explicitly to sections? | Current mapping is implicit via argumentative_flow |
| **All → All** | Should we have a shared "report context" object passed through? | Would ensure consistency but adds coupling |

---

## Future Considerations

- **Reprocessing**: Batch job to reprocess v1 documents with v2 Docling pipeline
- **MCP Integration**: Model Context Protocol servers for extended capabilities
- **Report Templates**: Customizable report formats
- **A/B Testing**: Compare v1 vs v2 output quality
