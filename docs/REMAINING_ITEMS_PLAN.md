# Remaining Items Plan: zena-deep-research → zena-workflow-spike

**Created:** December 17, 2025
**Status:** Planning
**Related:** `INTEGRATION_PLAN.md`

---

## Overview

This document tracks high-value items from `zena-deep-research` that have NOT been ported to `zena-workflow-spike`, plus new features to add.

---

## Part 1: Items to Port from zena-deep-research

### 1.1 Token Limit Handling

**Source:** `src/open_deep_research/utils.py` (lines 1207-1409)

**What it does:**
- Detects token/context limit exceeded errors across providers (OpenAI, Anthropic, Google)
- Progressive truncation retry logic (removes 10% of content per retry)
- Model-specific token limit lookup table

**Why it matters:**
- Prevents workflow failures when LLM context is exceeded
- Essential for large reports with many sections/sources

**Functions to port:**
- `is_token_limit_exceeded(exception, model_name)` - Detect overflow errors
- `get_model_token_limit(model_string)` - Lookup context limits
- `remove_up_to_last_ai_message(messages)` - Progressive truncation
- `MODEL_TOKEN_LIMITS` dict - Token limits by model

**Destination:** `workflows/shared/utils/token_limits.py`

---

### 1.2 Vector Store Embedding for Research Findings

**Source:** `src/open_deep_research/utils.py` (lines 589-643) + `vector_store.py`

**What it does:**
- Chunks compressed research into smaller pieces
- Embeds chunks into PostgreSQL pgvector
- Stores citation sources separately for lookup
- Enables retrieval during section expansion

**Why it matters:**
- Powers `search_research_findings` tool
- Enables "Derives From" sections to retrieve content from Deep Dive sections

**Functions to port:**
- Research findings chunking logic
- Citation source extraction and storage
- Vector store initialization pattern

**Destination:** `workflows/shared/utils/embeddings.py` or integrate into existing database operations

---

### 1.3 Additional Prompts (Non-Report Research)

**Source:** `src/open_deep_research/prompts.py`

**Prompts NOT yet ported:**
| Prompt | Purpose |
|--------|---------|
| `clarify_with_user_instructions` | Handle user clarification requests |
| `transform_messages_into_research_topic_prompt` | Refine research questions |
| `lead_researcher_prompt` | Main research supervisor |
| `research_system_prompt` | Individual researcher operations |
| `compress_research_system_prompt` | Research synthesis (different from report research) |
| `summarize_webpage_prompt` | Web content summarization |
| `summarize_internal_document_prompt` | Internal doc summarization |

**Destination:** `workflows/shared/prompts/research.py` (new file, separate from `report_research.py`)

---

### 1.4 Document Ingestion Enhancements

**Source:** `src/open_deep_research/document_ingester.py` + `ingest_initial_documents.py`

**What it does:**
- Docling integration with image description
- Multi-provider image description (OpenAI, Anthropic, Google)
- HybridChunker for semantic chunking

**Why it matters:**
- Better document understanding with image context
- More intelligent chunking than simple token splits

**Note:** Check if document ingestion v2 in workflow-spike already has these features. May be partially implemented.

**Destination:** Review `workflows/document_ingestion_workflow/` for gaps

---

### 1.5 Chunking Utilities

**Source:** `src/open_deep_research/chunks.py`

**What it does:**
- PDF text extraction with page tracking
- Token-based chunking using Chonkie library
- Overlap configuration for context continuity
- Metadata tracking (chunk index, token count, page number)

**Destination:** `workflows/shared/utils/chunking.py`

---

### 1.6 Complete Configuration Pattern

**Source:** `src/open_deep_research/configuration.py`

**What it does:**
- Search API abstraction (Tavily, OpenAI, Anthropic, None)
- MCP (Model Context Protocol) configuration
- `x_oap_ui_config` metadata for LangGraph Studio UI

**Note:** Basic config pattern was ported, but missing:
- `SearchAPI` enum
- MCP configuration support
- Search API selection logic

**Destination:** Enhance existing `workflows/*/config.py` files

---

### 1.7 Evaluation Framework

**Source:** `tests/evaluators.py`, `tests/prompts.py`, `tests/run_evaluate.py`

**What it does:**
- LLM-as-a-judge evaluation
- Quality metrics (depth, rigor, relevance, writing quality)
- LangSmith integration for tracking
- Deep Research Bench benchmarking

**Why it matters:**
- Validate v2 quality against v1
- Ongoing quality monitoring

**Destination:** `workflows/shared/evaluation/` or separate test infrastructure

---

## Part 2: New Feature - Visual Aids Suggestions

### 2.1 Overview

Add a node to the report generation workflow that analyzes the final report and suggests visual aids (charts, infographics, diagrams, tables) that would enhance the content.

**Use case:** Designer receives suggestions with enough context to create visual aids manually. Future: Agent with tools to auto-generate visuals.

---

### 2.2 Visual Aid Types

| Type | Description | Example Use Cases |
|------|-------------|-------------------|
| **Bar Chart** | Compare discrete categories | Market share comparison, competitor features |
| **Line Chart** | Show trends over time | Growth rates, historical performance |
| **Pie Chart** | Show composition/proportions | Market segments, budget allocation |
| **Table** | Structured data comparison | Feature matrix, pricing comparison |
| **Infographic** | Visual summary of key points | Executive summary highlights, process flows |
| **Process Diagram** | Show workflow or sequence | Customer journey, decision tree |
| **Comparison Matrix** | Side-by-side evaluation | Competitor SWOT, product comparison |
| **Timeline** | Chronological events | Product launch history, milestones |
| **Map** | Geographic data | Regional market presence, distribution |
| **Quadrant Chart** | 2x2 positioning | BCG matrix, competitive positioning |

---

### 2.3 Suggestion Schema

```python
class VisualAidSuggestion(TypedDict):
    """A suggestion for a visual aid to enhance the report."""

    # Location in report
    section_name: str  # Which section this visual would enhance
    placement: str  # "before", "after", or "replace" specific text
    anchor_text: str  # Text near where visual should be placed

    # Visual specification
    visual_type: str  # "bar_chart", "line_chart", "table", "infographic", etc.
    title: str  # Suggested title for the visual
    description: str  # What the visual should communicate

    # Data requirements
    required_data: list[dict]  # Specific data points needed
    # Example: [{"metric": "market_share", "entities": ["Brand A", "Brand B"], "source": "[3]"}]

    data_available: bool  # Whether data exists in the report
    data_location: str  # Where in report the data can be found, or "requires external data"

    # Design guidance
    key_message: str  # The "so what" - main takeaway
    design_notes: str  # Specific guidance for designer (colors, emphasis, etc.)

    # Priority
    impact: str  # "high", "medium", "low" - how much it would improve comprehension
    complexity: str  # "simple", "moderate", "complex" - effort to create
```

---

### 2.4 Node Implementation

**Node name:** `suggest_visual_aids_node`

**Placement in workflow:** After `finalize_report_node`, before `persist_report_node`

```
... → finalize_report → suggest_visual_aids → persist_report → END
```

**Input:**
- `final_report_markdown` - The complete report text
- `report_structure` - Section names and purposes
- `key_findings` - Extracted findings with data
- `sources` - All sources used

**Output:**
- `visual_aid_suggestions: list[VisualAidSuggestion]`

**Prompt approach:**
1. Analyze each section for data-rich content
2. Identify comparisons, trends, and statistics
3. Suggest appropriate visual type for each opportunity
4. Extract or reference the data needed
5. Provide clear guidance for designer

---

### 2.5 Prompt Template

```python
suggest_visual_aids_prompt = """You are a senior brand strategist and visual communication expert. Your task is to analyze a completed report and suggest visual aids that would enhance comprehension and impact.

Today's date is {date}.

<Report>
{final_report_markdown}
</Report>

<Report Structure>
{report_structure}
</Report Structure>

<Task>
Analyze the report and suggest visual aids (charts, infographics, tables, diagrams) that would:
1. Make complex data easier to understand
2. Highlight key comparisons or trends
3. Summarize important findings visually
4. Break up dense text sections
5. Reinforce the report's key messages
</Task>

<Guidelines>
1. **Prioritize impact**: Focus on visuals that would significantly improve comprehension
2. **Be specific about data**: Include exact numbers, categories, and sources from the report
3. **Consider feasibility**: Note whether data is available in the report or requires external sourcing
4. **Design guidance**: Provide enough detail for a designer to create the visual
5. **Don't over-suggest**: Quality over quantity - suggest 3-7 high-impact visuals, not one per paragraph
</Guidelines>

<Visual Types Available>
- Bar Chart: Compare discrete categories
- Line Chart: Show trends over time
- Pie Chart: Show composition/proportions
- Table: Structured data comparison
- Infographic: Visual summary of key points
- Process Diagram: Show workflow or sequence
- Comparison Matrix: Side-by-side evaluation
- Timeline: Chronological events
- Quadrant Chart: 2x2 positioning (e.g., competitive positioning)
- Map: Geographic data visualization
</Visual Types Available>

<Output Format>
For each suggestion, provide:

## Visual Aid {N}: {Title}

**Section:** {section_name}
**Type:** {visual_type}
**Placement:** {before/after/replace} "{anchor_text}"

**Description:** What this visual should show

**Required Data:**
- {data point 1} - Source: {citation or "in report" or "requires external data"}
- {data point 2} - ...

**Key Message:** The main takeaway this visual should communicate

**Design Notes:** Specific guidance (colors, emphasis, layout suggestions)

**Impact:** {High/Medium/Low}
**Complexity:** {Simple/Moderate/Complex}

---
</Output Format>

Analyze the report and provide your visual aid suggestions.
"""
```

---

### 2.6 State Updates

Add to `ReportStateV2` in `report_generation_workflow/state.py`:

```python
class VisualAidSuggestion(TypedDict, total=False):
    """A suggestion for a visual aid."""
    section_name: str
    placement: str
    anchor_text: str
    visual_type: str
    title: str
    description: str
    required_data: list[dict[str, Any]]
    data_available: bool
    data_location: str
    key_message: str
    design_notes: str
    impact: str
    complexity: str


class ReportStateV2(TypedDict, total=False):
    # ... existing fields ...

    # Visual aids
    visual_aid_suggestions: list[VisualAidSuggestion]
```

---

### 2.7 Configuration

Add to `ReportGenerationConfiguration`:

```python
# Visual Aids Configuration
suggest_visual_aids: bool = Field(
    default=True,
    metadata={
        "x_oap_ui_config": {
            "type": "boolean",
            "default": True,
            "description": "Whether to generate visual aid suggestions for the report",
        }
    },
)
visual_aids_model: str = Field(
    default="openai:gpt-4o",
    metadata={
        "x_oap_ui_config": {
            "type": "text",
            "default": "openai:gpt-4o",
            "description": "Model for generating visual aid suggestions",
        }
    },
)
max_visual_suggestions: int = Field(
    default=7,
    metadata={
        "x_oap_ui_config": {
            "type": "slider",
            "default": 7,
            "min": 3,
            "max": 15,
            "step": 1,
            "description": "Maximum number of visual aid suggestions to generate",
        }
    },
)
```

---

### 2.8 Output for Designer

The visual aid suggestions should be:
1. **Stored in database** with the generated report
2. **Exported as separate document** (markdown or JSON) for designer
3. **Included in API response** when report is retrieved

Example export format:

```markdown
# Visual Aid Suggestions for Report: {report_title}

Generated: {date}
Report ID: {report_id}

---

## 1. Market Share Comparison Chart

**Section:** Competitive Landscape
**Type:** Bar Chart
**Placement:** After "The market is dominated by three key players..."

**Description:** Horizontal bar chart comparing market share percentages for top 5 competitors.

**Required Data:**
| Competitor | Market Share | Source |
|------------|--------------|--------|
| Brand A | 35% | [1] |
| Brand B | 28% | [1] |
| Brand C | 18% | [2] |
| Others | 19% | Calculated |

**Key Message:** Brand A leads but Brand B is closing the gap

**Design Notes:**
- Use brand colors if available
- Highlight client's brand differently
- Include percentage labels on bars

**Impact:** High
**Complexity:** Simple

---

## 2. Consumer Journey Infographic
...
```

---

## Part 3: Implementation Priority

### Phase 1: Immediate (Before v2 Launch)

| Item | Priority | Effort | Notes |
|------|----------|--------|-------|
| Token limit handling | High | Low | Prevents failures |
| Additional prompts | High | Low | Copy and adapt |
| Visual aids node | High | Medium | New feature, high value |

### Phase 2: Near-term (v2 Stabilization)

| Item | Priority | Effort | Notes |
|------|----------|--------|-------|
| Vector store embedding | Medium | Medium | Already have search methods |
| Complete configuration | Medium | Low | Enhance existing |
| Chunking utilities | Medium | Low | May overlap with doc ingestion v2 |

### Phase 3: Future (Post-Launch)

| Item | Priority | Effort | Notes |
|------|----------|--------|-------|
| Evaluation framework | Low | High | For quality monitoring |
| Document ingestion enhancements | Low | Medium | Check for gaps first |
| Visual aid auto-generation | Low | High | Future agent with design tools |

---

## Part 4: Checklist

### Port from deep-research

- [ ] Token limit handling utilities
- [ ] Additional research prompts (non-report)
- [ ] Search API enum and selection logic
- [ ] Chunking utilities (if not in doc ingestion v2)
- [ ] Evaluation framework (optional)

### New Development

- [ ] `VisualAidSuggestion` schema in state.py
- [ ] `suggest_visual_aids_node` implementation
- [ ] Visual aids prompt (add to LangFuse)
- [ ] Configuration fields for visual aids
- [ ] Export format for designer
- [ ] API response updates

### Testing

- [ ] Test token limit handling with large reports
- [ ] Test visual aid suggestions on sample reports
- [ ] Validate suggestion quality with designer feedback
- [ ] Benchmark v2 vs v1 (if evaluation framework ported)

---

## References

- `zena-deep-research/src/open_deep_research/utils.py` - Token handling, embeddings
- `zena-deep-research/src/open_deep_research/prompts.py` - Additional prompts
- `zena-deep-research/src/open_deep_research/configuration.py` - Config patterns
- `zena-workflow-spike/zena/docs/INTEGRATION_PLAN.md` - Main integration plan
