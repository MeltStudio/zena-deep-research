# Frontend Requirements for V2 Workflows

**Date:** December 17, 2025 (Updated: December 22, 2025)
**Backend PR:** #76 - ✅ **MERGED** to main (December 22, 2025)
**Target Repository:** zena-web

---

## ⚠️ IMPORTANT: Document Rewritten December 22, 2025

The previous version of this document contained inaccuracies about section sketches in strategic plans. This version has been rewritten after a thorough code review to reflect what is **actually implemented**.

---

## Status: Backend Ready for Frontend Integration

The v2 workflows are merged and deployed.

### What's Deployed
- Strategic Planning v2 workflow
- Report Generation v3 workflow with conclusions/bibliography
- Database migrations for new fields

### What's NOT Implemented (Contrary to Previous Doc)
- ❌ Section sketches in strategic plans - NOT stored
- ❌ Structured `SectionSketch` objects - NOT returned by API
- ❌ New intermediate status values - NOT implemented

---

## Actual API Responses

### GET /strategic-plans/{id}

Returns:

```typescript
interface StrategicPlanDetail {
  id: string;
  report_id: string;
  workspace_id: string;
  strategic_hypothesis: string;        // The report plan TEXT (not structured)
  recommendations_framework: object | null;  // Currently empty {}
  argumentative_flow: object | null;         // Currently empty {}
  report_structure: object | null;           // Currently empty {} - NO SECTION SKETCHES
  key_findings: object | null;
  plan_validation_score: number | null;
  revision_count: number;
  status: string;
  feedback_text: string | null;
  created_at: string;
  updated_at: string;
}
```

**Key Points:**
- `strategic_hypothesis` contains the report plan as **plain text** (not structured sections)
- `report_structure` is **empty** (`{}`) - there are NO section sketches stored here
- Users approve/reject based on the text in `strategic_hypothesis`

### GET /generated-reports/{id}

Returns:

```typescript
interface GeneratedReportDetail {
  id: string;
  report_id: string | null;
  client_profile_id: string | null;
  problem_restatement_id: string | null;
  research_session_id: string | null;
  report_type: string | null;
  report_title: string;
  report_content_markdown: string;

  // NEW in v3 - these ARE implemented
  report_structure: {
    name: string;
    content_preview: string;  // First ~200 chars of section content
  }[] | null;
  executive_summary: string | null;
  conclusions: string | null;         // NEW
  bibliography: string | null;        // NEW

  key_findings: object | null;
  recommendations: object | null;
  sources_cited: object | null;
  validation_score: number | null;
  revision_count: number;
  status: string;
  file_path: string | null;
  s3_bucket: string | null;
  s3_key: string | null;
  created_at: string;
  updated_at: string;
}
```

**Key Points:**
- `conclusions` and `bibliography` are NEW fields ✅
- `report_structure` contains simple `{name, content_preview}` objects ✅
- NO `depth_level`, NO `sources[]`, NO structured section metadata

---

## What Frontend Needs to Implement

### Priority 1: Generated Report Display Updates

**File:** `generated-report-card.tsx` (or equivalent)

1. **Display new sections:**
   - `conclusions` - Render as markdown after main content
   - `bibliography` - Render as markdown at end of report

2. **Optional: Section navigation/TOC**
   - Use `report_structure[]` to build a clickable TOC
   - Each item has `name` and `content_preview`
   - Link to section headers in the markdown content

### Priority 2: Strategic Plan Review (NO CHANGES NEEDED)

The strategic plan approval flow works the same as before:
- Display `strategic_hypothesis` (the text plan)
- User clicks Approve or Reject
- No section sketches to display

**There is NO new UI for section sketches** - they don't exist in the strategic plan.

### Priority 3: Status Values (NO CHANGES NEEDED)

The status flow is unchanged. Current statuses are:

```typescript
type ReportStatus =
  | 'draft'
  | 'generating_plan'
  | 'plan_ready'
  | 'plan_approved'
  | 'researching'
  | 'research_ready'
  | 'research_approved'
  | 'planning'
  | 'planning_failed'
  | 'strategic_plan_ready'
  | 'strategic_plan_approved'
  | 'strategic_plan_rejected'
  | 'generating_report'
  | 'completed'
  | 'failed';
```

No new intermediate statuses (`expanding_sections`, `generating_standard_sections`) were added.

---

## Type Updates for `@meltstudio/client-common`

### Update GeneratedReport Type Only

```typescript
interface GeneratedReport {
  id: string;
  report_id: string | null;
  report_type: string | null;
  report_title: string;
  report_content_markdown: string;

  // NEW for v3
  conclusions: string | null;
  bibliography: string | null;
  report_structure: {
    name: string;
    content_preview: string;
  }[] | null;

  // Existing fields...
  executive_summary: string | null;
  key_findings: object | null;
  recommendations: object | null;
  sources_cited: object | null;
  validation_score: number | null;
  revision_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}
```

### StrategicPlan Type - NO CHANGES

The `StrategicPlan` type does not need updates. The `report_structure` field exists but is empty.

---

## Implementation Checklist

### Required for v3
- [ ] Add `conclusions` field to `GeneratedReport` type
- [ ] Add `bibliography` field to `GeneratedReport` type
- [ ] Update `report_structure` type to `{name, content_preview}[]`
- [ ] Display conclusions section in report view
- [ ] Display bibliography section in report view

### Optional Enhancements
- [ ] Add section navigation/TOC using `report_structure`
- [ ] Highlight current section during scroll

### NOT Needed (Previous Doc Was Wrong)
- ~~Section sketches in strategic plan review~~
- ~~SectionSketch type with depth_level, sources~~
- ~~Accordion UI for section sketches~~
- ~~Depth level badges (Deep Dive, Moderate, Surface-level)~~
- ~~New status values for progress tracker~~

---

## Summary of What Changed vs. What Was Promised

| Feature | Previous Doc Said | Actual Implementation |
|---------|------------------|----------------------|
| Section sketches in strategic plan | ✅ Yes, with structured objects | ❌ No - `report_structure` is empty |
| SectionSketch with name, content, sources, depth_level | ✅ Yes | ❌ No - never implemented |
| Depth level indicators | ✅ Deep Dive, Moderate, Surface-level | ❌ Not implemented |
| User reviews sketches before approval | ✅ Yes | ❌ No - user reviews text plan only |
| Conclusions field | ✅ Yes | ✅ Yes - works |
| Bibliography field | ✅ Yes | ✅ Yes - works |
| report_structure in GeneratedReport | ✅ Structured sections | ✅ Partial - just {name, content_preview} |
| New progress statuses | ✅ expanding_sections, generating_standard_sections | ❌ Not implemented |

---

## Future Work (If Needed)

If section sketches before approval are desired, this would require:

1. **Backend work:**
   - Add section sketch generation to strategic planning workflow
   - Persist sketches to `strategic_plans.report_structure`
   - Define structured schema for sketches

2. **Frontend work:**
   - Add section sketch display to plan review UI
   - Add depth level badges

This is NOT currently planned.

---

## Contact

Questions? Reach out to Manuel for clarification.
