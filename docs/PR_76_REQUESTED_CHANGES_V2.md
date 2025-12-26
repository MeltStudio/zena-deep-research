# PR #76 Requested Changes - Round 2

**Date:** December 19, 2025
**PR:** #76 - V2 Workflow Implementation
**Reviewers:** Manuel, Francisco

---

## Overview

Second round of changes based on Francisco's review comments. These changes improve the supervisor/researcher pattern consistency.

---

## Change 1: Add Iterative Research for Section Sketches

**File:** `zena/workflows/strategic_planning_workflow/nodes/supervisor_tools.py`

**Comment:** [#2628755094](https://github.com/Brantuit-AI/zena-workflow-spike/pull/76#discussion_r2628755094)

**Issue:** Currently does a single search call per section. Should follow the researcher pattern allowing iterative searching until the agent has enough information.

**Current Code (line 50):**
```python
# Search for relevant findings
findings_result = await search_research_findings.ainvoke(
    {"queries": [section_assignment]},
    config=config,
    report_id=report_id,
)
```

**Required Change:**
- Implement iterative research loop following the pattern from `research_workflow_v2`
- Allow the agent to search multiple times until it considers it has enough relevant information
- Use configurable max iterations

**Reference:** See `research_workflow/nodes/` for the researcher pattern implementation.

---

## Change 2: Use Compiled Subgraph for Supervisor

**File:** `zena/workflows/strategic_planning_workflow/graphv2.py`

**Comment:** [#2628726760](https://github.com/Brantuit-AI/zena-workflow-spike/pull/76#discussion_r2628726760)

**Issue:** The graph adds supervisor and tools as separate nodes instead of using a compiled subgraph.

**Current Code (lines 60-64):**
```python
# Add nodes
workflow.add_node("load_context", load_context_node)
workflow.add_node("create_report_plan", create_report_plan_node)
workflow.add_node("report_supervisor", report_supervisor_node)
workflow.add_node("supervisor_tools", supervisor_tools_node)
workflow.add_node("combine_sketches", combine_sketches_node)
```

**Required Change:**

Follow the pattern from `research_workflow/graphv2.py`:

```python
from zena.workflows.strategic_planning_workflow.nodes import (
    create_supervisor_sub_graph,  # NEW: Create subgraph factory
    ...
)

def create_strategic_planning_workflow_v2() -> CompiledStateGraph:
    ...

    # Create compiled subgraph for supervisor loop
    supervisor_subgraph = create_supervisor_sub_graph()

    # Add nodes
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("create_report_plan", create_report_plan_node)
    workflow.add_node("report_supervisor", supervisor_subgraph)  # Subgraph, not individual nodes
    workflow.add_node("combine_sketches", combine_sketches_node)
    workflow.add_node("persist_plan", persist_plan_node)
```

**Also required:** Create `create_supervisor_sub_graph()` function in `nodes/__init__.py` or a new `nodes/supervisor_subgraph.py` file.

---

## Change 3: Move Expansion Prompt to LangFuse

**File:** `zena/workflows/report_generation_workflow/nodes/supervisor_tools_v2.py`

**Comment:** [#2628764037](https://github.com/Brantuit-AI/zena-workflow-spike/pull/76#discussion_r2628764037)

**Issue:** The expansion prompt is hardcoded inline instead of being fetched from LangFuse.

**Current Code (lines 44-62):**
```python
expansion_prompt = f"""Expand this section sketch into full report content.

## Section: {section_name}

## Original Sketch
{sketch}

## Additional Research
{findings_result}

## Expansion Guidance
{guidance if guidance else 'Expand with additional detail, examples, and analysis.'}

Write the full section content:
1. Maintain all existing citations from the sketch
2. Add new citations from the research findings
3. Elaborate on key points with supporting evidence
4. Ensure professional tone suitable for executive audience
5. Keep citations in [N] format"""
```

**Required Changes:**

### 3a. Add accessor function to `report_prompts.py`

**File:** `zena/workflows/shared/prompts/report_prompts.py`

```python
def get_execute_section_expansion_prompt(
    section_name: str,
    sketch: str,
    findings: str,
    guidance: str,
) -> str:
    """Get the prompt for expanding a section sketch into full content.

    Args:
        section_name: Name of the section being expanded
        sketch: The original section sketch content
        findings: Additional research findings
        guidance: Optional expansion guidance from supervisor

    Returns:
        Compiled prompt string
    """
    return get_prompt(
        "execute_section_expansion",
        date=get_today_str(),
        section_name=section_name,
        sketch=sketch,
        findings=findings,
        guidance=guidance,
    )
```

### 3b. Update `__init__.py` exports

**File:** `zena/workflows/shared/prompts/__init__.py`

Add to imports and `__all__`:
```python
from zena.workflows.shared.prompts.report_prompts import (
    ...
    get_execute_section_expansion_prompt,  # NEW
)

__all__ = [
    ...
    "get_execute_section_expansion_prompt",  # NEW
]
```

### 3c. Create prompt in LangFuse

**Prompt name:** `execute_section_expansion`

```
Expand this section sketch into full report content.

## Today's Date
{{date}}

## Section: {{section_name}}

## Original Sketch
{{sketch}}

## Additional Research
{{findings}}

## Expansion Guidance
{{guidance}}

Write the full section content:
1. Maintain all existing citations from the sketch
2. Add new citations from the research findings
3. Elaborate on key points with supporting evidence
4. Ensure professional tone suitable for executive audience
5. Keep citations in [N] format
```

### 3d. Update node to use LangFuse prompt

**File:** `zena/workflows/report_generation_workflow/nodes/supervisor_tools_v2.py`

```python
from zena.workflows.shared.prompts import get_execute_section_expansion_prompt

# Replace inline prompt with:
expansion_prompt = get_execute_section_expansion_prompt(
    section_name=section_name,
    sketch=sketch,
    findings=findings_result,
    guidance=guidance if guidance else "Expand with additional detail, examples, and analysis.",
)
```

---

## Change 4: Remove Expansion Supervisor

**File:** `zena/workflows/report_generation_workflow/graphv2.py` and related nodes

**Comment:** [#2628786619](https://github.com/Brantuit-AI/zena-workflow-spike/pull/76#discussion_r2628786619)

**Issue:** The expansion supervisor is redundant if it's just assigning all sections the same way without making intelligent decisions.

**Francisco's comment:**
> "This is fine. I think that at this step we don't need any iteration. If all sections are always going to use the same values, we probably don't need a supervisor to assign them. Instead, we could just create a node that makes a call for each section. In that case, the supervisor becomes redundant, and if we remove it, we should also remove its configuration."

**Required Changes:**

1. **Replace supervisor loop with simple parallel expansion node:**
   - Create new node `expand_all_sections_node` that:
     - Takes all section sketches from state
     - Expands each section in parallel using `_execute_section_expansion()`
     - Returns all expanded sections

2. **Update graph structure:**
   - Remove `expansion_supervisor` node
   - Remove `supervisor_tools` node
   - Add single `expand_all_sections` node
   - Update edges accordingly

3. **Remove supervisor configuration:**
   - Remove `expansion_supervisor_model` from config
   - Remove `max_expansion_iterations` from config
   - Keep `section_expander_model` and `max_concurrent_section_expansions`

4. **Clean up unused files:**
   - Remove or repurpose `expansion_supervisor.py`
   - Update `supervisor_tools_v2.py` to just contain `_execute_section_expansion()` helper

---

## Change 5: Pending - Sketch Truncation

**File:** `zena/workflows/report_generation_workflow/nodes/supervisor_tools_v2.py`

**Comment:** [#2628764678](https://github.com/Brantuit-AI/zena-workflow-spike/pull/76#discussion_r2628764678)

**Issue:** Sketch is truncated to 500 chars for search query.

**Status:** Waiting for Francisco's response on preferred approach.

---

## Checklist

- [ ] Change 1: Add iterative research loop in `supervisor_tools.py`
- [ ] Change 2: Refactor to use compiled subgraph pattern
- [ ] Change 3a: Add `get_execute_section_expansion_prompt` to `report_prompts.py`
- [ ] Change 3b: Update `__init__.py` exports
- [ ] Change 3c: Create `execute_section_expansion` prompt in LangFuse
- [ ] Change 3d: Update node to use LangFuse prompt
- [ ] Change 4: Remove expansion supervisor, create simple parallel expansion node
- [ ] Change 5: (Pending Francisco's response)

---

## Questions?

Reach out to Manuel if anything is unclear.
