# Discussion Items for Francisco - December 23, 2025

## Summary

After merging PR #76 (v2 workflows) and preparing frontend requirements, we discovered significant gaps between what was planned and what was implemented. This document outlines the issues that need resolution.

---

## Issue 1: Section Sketches Not Implemented in Strategic Planning

### What Was Planned (Integration Plan)

The design called for users to review section-level sketches before approving the strategic plan:

1. Strategic Planning v2 generates section sketches with:
   - `name` - Section title
   - `content` - Draft outline/sketch content
   - `sources` - Citations used
   - `depth_level` - "Deep Dive" | "Moderate Analysis" | "Surface-level"

2. Sketches stored in `strategic_plans.report_structure`

3. Users review section sketches in the UI before clicking "Approve"

4. This gives users visibility into report structure before full generation begins

### What Was Actually Implemented

1. Strategic Planning v2 generates a text-based `report_plan` stored in `strategic_hypothesis`

2. `report_structure` is saved as **empty** `{}`

3. Section sketches are created **during report generation** (in `report_supervisor` step), not during strategic planning

4. Users only see section-level detail **after** the report is already generated

### Code Evidence

**`persist_strategic_plan.py:55-66`:**
```python
strategic_plan_id = db_manager.save_strategic_plan(
    report_id=report_id,
    workspace_id=workspace_id,
    strategic_hypothesis=report_plan,
    recommendations_framework={},
    argumentative_flow={},
    report_structure={},  # <-- EMPTY
    key_findings={},
    ...
)
```

**`state.py` (Strategic Planning):**
```python
class StrategicPlanningStateV2(TypedDict):
    report_plan: str  # <-- Just a string, not structured sections
    ...
```

### Impact

- Users approve strategic plans without seeing section-level detail
- The "review before generation" workflow doesn't exist
- Frontend was about to build UI for a feature that isn't there
- This was a key differentiator in the v2 design

### Questions

1. Was this an intentional scope reduction, or was it missed during implementation?
2. Should we add section sketch generation to the strategic planning workflow?
3. If yes, what's the priority vs. other work?
4. What should the structured schema for sketches look like?

---

## Issue 2: Research Workflow v2 Status

### Current State

- `research_workflow/graphv2.py` exists in the codebase
- The Celery task (`research_tasks.py`) has a `use_v2` flag that defaults to `False`
- Research in production still uses v1

### From the Cleanup Email

The cleanup PR instructions tell the Python team to **delete** `research_workflow/graphv2.py`.

### Questions

1. Is research v2 something we want to keep and enable?
2. Or should we delete it as instructed in the cleanup email?
3. If we keep it, when would we enable it?

---

## Issue 3: Missing Features from Original Plan

These were in the original frontend requirements doc but are NOT implemented:

| Feature | Status | Notes |
|---------|--------|-------|
| `SectionSketch` structured type | ❌ Not implemented | Was supposed to have name, content, sources, depth_level |
| Depth level indicators | ❌ Not implemented | "Deep Dive", "Moderate Analysis", "Surface-level" |
| Intermediate progress statuses | ❌ Not implemented | `expanding_sections`, `generating_standard_sections` |
| Section-level sources in sketches | ❌ Not implemented | Sources array per section |

### Questions

1. Which of these features are still desired?
2. What's the priority for implementing them?
3. Should we create tickets for them?

---

## What IS Working

To be clear, these features ARE implemented and working:

| Feature | Status |
|---------|--------|
| Strategic Planning v2 (text-based plan) | ✅ Working |
| Report Generation v3 | ✅ Working |
| `conclusions` field in GeneratedReport | ✅ Working |
| `bibliography` field in GeneratedReport | ✅ Working |
| `report_structure` with {name, content_preview} in GeneratedReport | ✅ Working |
| ResearchFinding table with embeddings | ✅ Deployed |
| Research search tools | ✅ Deployed |

---

## Recommended Actions

### Option A: Add Section Sketches to Strategic Planning (Recommended)

1. Create new node in strategic planning workflow to generate section sketches
2. Define structured schema for `SectionSketch`
3. Persist sketches to `strategic_plans.report_structure`
4. Frontend builds review UI
5. Estimated effort: 2-3 days backend + frontend

### Option B: Accept Current Implementation

1. Users approve based on text plan only
2. Section detail only visible in final report
3. Update integration plan to reflect this is intentional
4. No additional work needed

---

## Files Changed

For reference, these docs were updated today:

1. `docs/FRONTEND_V2_REQUIREMENTS.md` - Rewritten to reflect actual implementation
2. `docs/INTEGRATION_PLAN.md` - Updated with completed phases and pending items

---

## Next Steps

1. Review this document with Francisco
2. Decide on section sketches: implement or accept current behavior
3. Decide on research v2: keep or delete
4. Update integration plan with decisions
5. Communicate final plan to frontend team
