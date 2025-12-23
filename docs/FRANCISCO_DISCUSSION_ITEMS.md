# Discussion Items for Francisco - December 23, 2025

## Summary

Two items need discussion/decision for v2 workflows.

---

## Issue 1: Section Sketches - Clarifying the UX Flow

### What's Implemented

Section sketches ARE implemented, but in the **Report Generation** workflow, not Strategic Planning:

1. **Strategic Planning v2** → generates text `report_plan` (stored in `strategic_hypothesis`)
2. **Report Generation v3** → `report_supervisor` delegates sections to `report_researcher` subgraph
3. **Report Researcher** → does research, compresses, then `write_report_section` generates `report_section_sketch`
4. **Persist Report v3** → saves sketches to `generated_reports.report_structure` as `{name, content_preview}`

### Current UX Flow

1. User reviews strategic plan (text-based `strategic_hypothesis`)
2. User approves → triggers report generation
3. Report generation creates section sketches internally
4. User sees sketches only in the **final generated report**

### Question for Francisco

**Is this the intended UX?**

- **Current:** User approves plan first, then sees sketches after report is complete
- **Alternative:** User could preview sketches before full report generation (would require moving sketch generation earlier)

If current flow is intentional, no changes needed.

---

## Issue 2: Structured API Response Fields - NEEDED

The following fields are used internally (in prompts/LLM context) but NOT exposed in the API response. These need to be added:

| Feature | Current State | What's Needed |
|---------|---------------|---------------|
| `SectionSketch` structured type | Sketches are `list[str]` | Structured objects with `name`, `content`, `sources`, `depth_level` |
| Depth level per section | Embedded in text (used by LLM) | Expose as separate field in API response |
| Section-level sources | Embedded in sketch text | Expose as `sources[]` array per section |

### Work Required

1. **Update `report_section_sketch` output** - Change from plain string to structured object
2. **Parse/extract depth_level** - From the report_plan or section assignment
3. **Parse/extract sources** - From the sketch content into a separate array
4. **Update `persist_reportv3.py`** - Save structured sketches to `report_structure`
5. **Update API schema** - `GeneratedReportDetail.report_structure` to include new fields

### Questions for Francisco

1. Should we parse sources from the sketch text, or have the LLM output them separately?
2. Should depth_level come from the report_plan (input) or be determined by the researcher?
3. Priority for this work vs other items?

---

## Recommended Actions

### Issue 1: Section Sketch UX Flow
- **Action:** Confirm with Francisco if current flow is intentional
- **If yes:** No changes needed
- **If no:** Plan work to add sketch preview before report generation

### Issue 2: Structured API Response
- **Action:** Add structured `SectionSketch` fields to API response
- **Work items:**
  1. Update sketch output to structured object (name, content, sources, depth_level)
  2. Update persist_reportv3.py to save structured data
  3. Update API schema
- **Estimate:** 1-2 days backend
