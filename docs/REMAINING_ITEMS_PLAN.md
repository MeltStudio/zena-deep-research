# Remaining Items Plan: zena-deep-research → zena-workflow-spike

**Created:** December 17, 2025
**Status:** Planning
**Related:** `INTEGRATION_PLAN.md`

---

## Overview

This document tracks high-value items from `zena-deep-research` that have NOT yet been ported to `zena-workflow-spike`.

**Note:** Once all items are ported, this repository can be safely deleted.

---

## Items to Port

### 1. Token Limit Handling

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

### 2. Vector Store Embedding for Research Findings

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

### 3. Additional Prompts (Non-Report Research)

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

### 4. Document Ingestion Enhancements

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

### 5. Chunking Utilities

**Source:** `src/open_deep_research/chunks.py`

**What it does:**
- PDF text extraction with page tracking
- Token-based chunking using Chonkie library
- Overlap configuration for context continuity
- Metadata tracking (chunk index, token count, page number)

**Destination:** `workflows/shared/utils/chunking.py`

---

### 6. Complete Configuration Pattern

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

### 7. Evaluation Framework

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

## Implementation Priority

### Phase 1: Immediate (Before v2 Launch)

| Item | Priority | Effort | Notes |
|------|----------|--------|-------|
| Token limit handling | High | Low | Prevents failures |
| Additional prompts | High | Low | Copy and adapt |

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

---

## Checklist

- [ ] Token limit handling utilities
- [ ] Additional research prompts (non-report)
- [ ] Search API enum and selection logic
- [ ] Chunking utilities (if not in doc ingestion v2)
- [ ] Evaluation framework (optional)
- [ ] Document ingestion image description (if not already implemented)

---

## References

- `zena-deep-research/src/open_deep_research/utils.py` - Token handling, embeddings
- `zena-deep-research/src/open_deep_research/prompts.py` - Additional prompts
- `zena-deep-research/src/open_deep_research/configuration.py` - Config patterns
- `zena-workflow-spike/zena/docs/INTEGRATION_PLAN.md` - Main integration plan
