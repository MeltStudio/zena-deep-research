# Discussion Items for Francisco - December 23, 2025

## All Items Resolved

Both issues have been clarified and resolved.

---

## Issue 1: Section Sketches UX Flow - ✅ RESOLVED

**Decision:** Current flow is intentional.

- Sketches are internal to report generation workflow
- Users do NOT see or approve sketches - they were moved to report generation specifically to avoid an approval step
- No UI needed for sketches
- No API changes needed

---

## Issue 2: Structured API Response Fields - ✅ NOT NEEDED

**Decision:** Sketches don't need to be exposed in API.

Since sketches are internal and not displayed to users:
- No need for structured `SectionSketch` type in API
- No need to expose `depth_level`, `sources` as separate fields
- Current `report_structure` with `{name, content_preview}` is sufficient for TOC/navigation

---

## Summary

No additional backend work required. The v2 integration is complete.
