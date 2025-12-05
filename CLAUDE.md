# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Open Deep Research is a configurable deep research agent built on LangGraph that conducts automated research with parallel processing and generates comprehensive reports. It supports multiple LLM providers (OpenAI, Anthropic, Google, Groq, DeepSeek), search APIs (Tavily, native Anthropic/OpenAI web search), and MCP servers.

## Development Commands

```bash
# Start development server with LangGraph Studio
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking

# Run evaluations against Deep Research Bench (costs ~$20-$100)
python tests/run_evaluate.py

# Linting and type checking
ruff check src/
mypy src/

# Install dependencies
uv sync
```

## Architecture

### Main Graph (`src/open_deep_research/deep_researcher.py`)

The agent uses a hierarchical LangGraph structure with three compiled subgraphs:

```
deep_researcher (main graph)
├── clarify_with_user → Optional clarification phase
├── write_research_brief → Transforms user input into research brief
├── research_supervisor (subgraph) → Manages research delegation
│   ├── supervisor → Plans research strategy, uses ConductResearch/ResearchComplete tools
│   └── supervisor_tools → Executes tool calls, spawns researcher subgraphs
└── final_report_generation → Synthesizes all findings into report
```

**Researcher Subgraph** (spawned in parallel by supervisor):
```
researcher_subgraph
├── researcher → Conducts focused research using search/MCP tools
├── researcher_tools → Executes search queries
└── compress_research → Summarizes findings before returning to supervisor
```

### State Flow

- `AgentState` → Main graph state (messages, research_brief, notes, final_report)
- `SupervisorState` → Supervisor subgraph state (supervisor_messages, research_iterations)
- `ResearcherState` → Individual researcher state (researcher_messages, tool_call_iterations)

The `override_reducer` in `state.py` allows state values to be either appended or completely replaced using `{"type": "override", "value": ...}`.

### Key Configuration Fields (`src/open_deep_research/configuration.py`)

All configurable via environment variables (UPPERCASE) or LangGraph Studio UI:
- `search_api`: tavily, openai, anthropic, or none
- `research_model`, `compression_model`, `final_report_model`: Model selection per task
- `max_concurrent_research_units`: Parallel research tasks (default: 5)
- `max_researcher_iterations`: Supervisor reflection loops (default: 6)
- `max_react_tool_calls`: Tool calls per researcher (default: 10)

### Tools System (`src/open_deep_research/utils.py`)

Tools are assembled dynamically in `get_all_tools()`:
1. Core tools: `ResearchComplete`, `think_tool`, `search_internal_documents`
2. Search tool based on `search_api` config
3. MCP tools if configured

The `tavily_search` tool includes automatic summarization of webpage content using the summarization model.

## Environment Variables

Required (copy from `.env.example`):
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` - Model provider keys
- `TAVILY_API_KEY` - For Tavily search
- `LANGSMITH_API_KEY` - For tracing and evaluation

## Testing & Evaluation

The `tests/` directory contains evaluation infrastructure for Deep Research Bench:
- `run_evaluate.py` - Main entry point, configures models and runs against LangSmith dataset
- `evaluators.py` - Quality, relevance, structure, correctness, groundedness, completeness evaluators
- `extract_langsmith_data.py` - Exports results to JSONL for benchmark submission
