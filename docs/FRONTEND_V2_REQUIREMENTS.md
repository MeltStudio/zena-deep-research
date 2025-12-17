# Frontend Requirements for V2 Workflows

**Date:** December 17, 2025
**Related PR:** #76 - V2 Workflow Implementation
**Target Repository:** zena-web

---

## Overview

The v2 workflow implementation introduces several new features that require frontend updates. This document outlines what the frontend team needs to implement to support these changes.

The v2 workflows add:
1. **Section sketches** in strategic plans (user reviews before report generation)
2. **Section-level structure** with depth levels and dependencies

> **Note:** Report versioning and per-section feedback are deferred to future PRs. See "Future Work" section.

---

## Priority 1: Strategic Plan Review Enhancement

### What Changed

The strategic plan now includes **section sketches** - draft outlines for each report section that users can review before full report generation begins.

### New Data Structure

The `StrategicPlan` object now contains:

```typescript
interface StrategicPlan {
  // Existing fields...
  strategic_hypothesis: string;
  plan_validation_score: number;
  key_findings: { key_insights: KeyInsight[] };

  // NEW: Section sketches from v2
  report_structure: {
    sections: SectionSketch[];
  };
}

interface SectionSketch {
  section_name: string;      // e.g., "Key Q & A", "Bases of Comparison"
  content: string;           // Draft outline/sketch content (markdown)
  sources: string[];         // Citation sources used
  depth_level: string;       // "Deep Dive" | "Moderate Analysis" | "Surface-level"
}
```

### UI Requirements

**Update `hypothesis-review-card.tsx`** to display section sketches:

1. **Add "Report Sections" tab or accordion** showing all section sketches
2. **For each section, display:**
   - Section name with depth level badge (color-coded)
     - Deep Dive: Blue/Primary
     - Moderate Analysis: Yellow/Warning
     - Surface-level: Gray/Muted
   - Sketch content (rendered markdown)
   - Source count indicator
   - Expandable sources list

3. **Section order** should match the order in `report_structure.sections`

4. **Approval flow remains the same** - user approves/rejects the entire strategic plan (including sketches)

### Mockup Suggestion

```
┌─────────────────────────────────────────────────────────────┐
│ Strategic Plan Review                                        │
├─────────────────────────────────────────────────────────────┤
│ [Strategic Hypothesis Tab] [Section Sketches Tab] [Findings] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Section Sketches (7 sections)                                │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ▼ Key Q & A                            [Deep Dive] 🔵   │ │
│ │   ───────────────────────────────────────────────────── │ │
│ │   This section will address the 12 strategic questions  │ │
│ │   provided by the client, including:                    │ │
│ │   - Competitive landscape positioning [1]               │ │
│ │   - Market share trends [2][3]                         │ │
│ │   - Growth opportunities...                            │ │
│ │                                                        │ │
│ │   📚 3 sources                                          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ▶ Bases of Comparison                  [Deep Dive] 🔵   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ▶ Vulnerability Assessment        [Moderate] 🟡         │ │
│ │   Derives from: Bases of Comparison                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│              [Reject with Feedback]  [Approve Plan]          │
└─────────────────────────────────────────────────────────────┘
```

---

## ~~Priority 2: Report Version History~~ (DEFERRED)

> **NOTE:** Report versioning is deferred until report approval/rejection is implemented. Without an approval step, there's no mechanism to create new versions. This will be addressed in a future PR.

See "Future Work" section at the end of this document.

---

## Priority 2: Report Section Display

### What Changed

Reports now have a clear **section structure** with metadata about each section's depth level.

### New Data Structure

The `GeneratedReport` now includes section metadata:

```typescript
interface GeneratedReport {
  // Existing...
  report_content_markdown: string;

  // NEW: Section structure
  report_structure: {
    name: string;
    content_preview: string;  // First 200 chars
  }[];

  // Standard sections (always present)
  executive_summary: string;
  conclusions: string;
  bibliography: string;
}
```

### UI Requirements

**Update `generated-report-card.tsx`:**

1. **Add section navigation/TOC**
   - Clickable section links that scroll to section
   - Show section names from `report_structure`

2. **Clearly separate standard sections**
   - Executive Summary (at top, before content sections)
   - Content Sections (from strategic plan)
   - Conclusions
   - Bibliography

3. **Section anchors in markdown**
   - Add anchor IDs to section headers for navigation

---

## Priority 3: Progress Tracker Updates

### What Changed

The workflow now has more granular stages during strategic planning and report generation.

### New Status Values

Add support for these intermediate statuses:

```typescript
type ReportStatus =
  | 'draft'
  | 'generating_plan'
  | 'plan_ready'
  | 'plan_approved'
  | 'researching'
  | 'research_ready'
  | 'research_approved'
  | 'planning'                    // Strategic planning in progress
  | 'planning_failed'
  | 'strategic_plan_ready'
  | 'strategic_plan_approved'
  | 'strategic_plan_rejected'
  | 'generating_report'
  | 'expanding_sections'          // NEW: Section expansion in progress
  | 'generating_standard_sections' // NEW: Exec summary, conclusions, etc.
  | 'completed'
  | 'failed';
```

### UI Requirements

**Update `report-progress-tracker.tsx`:**

1. **Add sub-steps** for report generation phase:
   - "Expanding sections" (shows during section expansion)
   - "Generating summary & conclusions" (during standard sections)

2. **Show section progress** (optional enhancement):
   - "Expanding section 3 of 7..."

---

## ~~Priority 4: Section-Level Feedback~~ (DEFERRED)

> **NOTE:** Section-level feedback is deferred. See "Future Work" section.

---

## API Changes Summary

### Existing Endpoints (Updated Response)

| Endpoint | Change |
|----------|--------|
| `GET /reports/{id}` | Response now includes `version`, `report_structure` with section sketches |
| `GET /strategic_plans/{id}` | Response now includes `report_structure.sections` with sketches |

### New Endpoints Needed (v2 Launch)

None required for initial v2 launch. Version history and report approval endpoints are deferred.

### Existing Endpoints (No Change)

These continue to work as before:
- `POST /strategic_plans/{id}/approve`
- `POST /strategic_plans/{id}/reject`
- `POST /problem_restatements/{id}/approve`
- `POST /problem_restatements/{id}/reject`

---

## Type Updates for `@meltstudio/client-common`

Update these types in the shared types package:

```typescript
// Add to StrategicPlan
interface StrategicPlan {
  id: string;
  strategic_hypothesis: string;
  plan_validation_score: number;
  key_findings: { key_insights: KeyInsight[] };

  // NEW
  report_structure: {
    sections: SectionSketch[];
  };
}

interface SectionSketch {
  section_name: string;
  content: string;
  sources: string[];
  depth_level: 'Deep Dive' | 'Moderate Analysis' | 'Surface-level';
}

// Add to GeneratedReport
interface GeneratedReport {
  id: string;
  report_title: string;
  report_content_markdown: string;
  executive_summary: string;

  // NEW for v2
  conclusions: string;
  bibliography: string;
  report_structure: {
    name: string;
    content_preview: string;
  }[];

  // DEFERRED (future PR)
  // version: number;
  // status: 'draft' | 'approved';
  // feedback_text: string;
}
```

---

## Implementation Checklist

### Phase 1: Strategic Plan Section Sketches (Required for v2 launch)
- [ ] Update `StrategicPlan` type to include `report_structure.sections`
- [ ] Add `SectionSketch` type
- [ ] Update `hypothesis-review-card.tsx` to display section sketches
- [ ] Add depth level badges with color coding
- [ ] Test approval flow with new data structure

### Phase 2: Report Display Enhancements (Required for v2 launch)
- [ ] Update `GeneratedReport` type with new fields (`conclusions`, `bibliography`, `report_structure`)
- [ ] Add section navigation/TOC to `generated-report-card.tsx`
- [ ] Display conclusions and bibliography sections

### Phase 3: Progress Tracker Updates (Optional for v2 launch)
- [ ] Add new status values to `ReportStatus` type
- [ ] Update `report-progress-tracker.tsx` with sub-steps
- [ ] Add section progress indicators

---

## Future Work (Separate PRs)

The following features are **NOT part of v2 launch** and will be implemented in future PRs:

### Report Approval/Rejection Flow
- Add `POST /generated-reports/{id}/actions/approve` endpoint
- Add `POST /generated-reports/{id}/actions/reject` endpoint
- Add `feedback_text` field to `GeneratedReport` model
- Add approval UI to `generated-report-card.tsx`
- Implement report regeneration workflow based on feedback

### Report Version History
- Add `version` field to `GeneratedReport`
- Add `GET /reports/{id}/versions` endpoint
- Add `GET /reports/{id}/versions/{ver}` endpoint
- Create `/zena-reports/[id]/versions/` page
- Add `useReportVersionHistory()` hook
- Add version comparison view

### Per-Section Feedback
- Add `section_feedback` field to `GeneratedReport`
- Add per-section feedback API endpoints
- Add feedback button per section in UI
- Implement per-section regeneration workflow

---

## Questions for Frontend Team

1. **Section sketches display:** Tabs vs accordion vs separate page?
2. **Version history:** Inline panel vs separate page?
3. **Depth level colors:** Match existing design system or new palette?
4. **Mobile responsiveness:** How should section sketches display on mobile?

---

## API Reference

The following API fields are available for v2 (PR #76):

| Endpoint                    | Field             | Type   | Description                     |
|-----------------------------|-------------------|--------|---------------------------------|
| GET /generated-reports/{id} | executive_summary | string | Executive summary text          |
| GET /generated-reports/{id} | conclusions       | string | Conclusions section text        |
| GET /generated-reports/{id} | bibliography      | string | Bibliography section text       |
| GET /generated-reports/{id} | report_structure  | object | Section previews                |
| GET /strategic-plans/{id}   | report_structure  | object | Full plan with section sketches |

---

## Contact

Reach out to Manuel if anything is unclear or if you need clarification on the backend data structures.
