# Evaluation Framework Plan

**Created:** December 17, 2025
**Status:** Future Enhancement
**Priority:** Low (post-launch)

---

## Overview

This document outlines the plan for implementing report quality evaluation in `zena-workflow-spike`. Rather than porting the custom evaluation code from `zena-deep-research`, we will leverage Langfuse's built-in evaluation features.

---

## Why Langfuse Instead of Custom Code

The original `zena-deep-research` evaluation framework (`tests/evaluators.py`, `tests/prompts.py`, `tests/run_evaluate.py`) implemented:
- Custom LLM-as-judge functions
- Quality metrics (depth, rigor, relevance, writing quality)
- LangSmith integration for tracking

**Langfuse now provides all of this natively:**

| Custom Code Approach | Langfuse Native Approach |
|---------------------|-------------------------|
| Custom evaluator functions | Managed evaluators + custom templates |
| Manual LLM calls for judging | Built-in LLM-as-a-Judge with execution tracing |
| LangSmith for tracking | Langfuse scores + dashboards |
| Custom benchmark scripts | Datasets + Experiments |
| Manual prompt management | Evaluator library with versioning |

**Benefits of using Langfuse:**
- No code to maintain
- UI for creating/editing evaluation prompts
- Automatic execution tracing for debugging
- Sampling for cost control
- Integration with existing Langfuse observability
- Ragas-maintained evaluators for common metrics

---

## Langfuse Evaluation Features

### 1. LLM-as-a-Judge

Langfuse's LLM-as-a-Judge evaluates traces using an LLM to score and provide reasoning.

**Setup:**
1. Configure LLM connection (OpenAI, Anthropic, Bedrock, etc.)
2. Choose evaluator (managed or custom template)
3. Map variables (trace input/output to prompt variables)
4. Configure sampling and filters

**Execution tracing:** Every evaluation creates a trace showing the exact prompt, response, and token usage.

### 2. Managed Evaluators

Pre-built evaluators maintained by Langfuse and partners (Ragas):

| Evaluator | Description |
|-----------|-------------|
| **Hallucination** | Detects fabricated information |
| **Helpfulness** | Measures response usefulness |
| **Relevance** | Assesses alignment with query |
| **Toxicity** | Flags harmful content |
| **Correctness** | Compares to expected output |
| **Context Relevance** | RAG-specific: retrieved context relevance |
| **Conciseness** | Evaluates response brevity |

### 3. Custom Evaluators

For report-specific quality dimensions, create custom evaluator templates:

```
{{input}}     - The research brief/questions
{{output}}    - The generated report
{{context}}   - Optional: research findings used
```

**Proposed custom evaluators for reports:**

| Evaluator | Description | Score Range |
|-----------|-------------|-------------|
| `report_depth` | Thoroughness of topic coverage | 0-1 |
| `report_rigor` | Quality of reasoning and evidence | 0-1 |
| `citation_quality` | Proper use of sources and citations | 0-1 |
| `strategic_value` | Actionable insights and recommendations | 0-1 |
| `writing_quality` | Clarity, structure, professionalism | 0-1 |

### 4. Datasets & Experiments

**Datasets:** Collection of test inputs with expected outputs for benchmarking.

**Experiments:** Run workflows against datasets and automatically score results.

**Use case:** Compare v1 vs v2 report quality systematically.

### 5. Custom Scores via SDK

For runtime evaluations not suitable for LLM-as-judge:

```python
from langfuse import Langfuse

langfuse = Langfuse()

# Score a trace
langfuse.score(
    trace_id="...",
    name="report_length",
    value=len(report_text),
    data_type="NUMERIC",
)

# Categorical score
langfuse.score(
    trace_id="...",
    name="report_type",
    value="competitive_analysis",
    data_type="CATEGORICAL",
)
```

---

## Implementation Plan

### Phase 1: Production Monitoring (Immediate)

Set up basic quality monitoring on production traces:

1. **Enable managed evaluators** on report generation traces:
   - Hallucination (sample 10% of traces)
   - Helpfulness (sample 10% of traces)

2. **Create dashboard** to track scores over time

3. **Set up alerts** for low scores

### Phase 2: Custom Report Evaluators (Near-term)

Create report-specific evaluators:

1. **report_depth** - Custom template evaluating topic coverage
2. **citation_quality** - Custom template checking source usage
3. **strategic_value** - Custom template assessing actionability

### Phase 3: Benchmark Dataset (Future)

Create a benchmark dataset for systematic comparison:

1. Curate 20-30 representative research briefs
2. Generate reports with v1 and v2 workflows
3. Run all evaluators on both sets
4. Compare aggregate scores

---

## Evaluator Prompt Templates

### Report Depth Evaluator

```
You are evaluating the depth and thoroughness of a research report.

<Research Brief>
{{input}}
</Research Brief>

<Generated Report>
{{output}}
</Generated Report>

Evaluate how thoroughly the report covers the topics in the research brief.

Consider:
1. Are all key questions addressed?
2. Is there sufficient detail for each topic?
3. Are complex topics explored with appropriate depth?
4. Are there obvious gaps or missing information?

Score from 0 to 1:
- 0.0-0.3: Superficial, missing major topics
- 0.4-0.6: Adequate coverage, some gaps
- 0.7-0.8: Good depth, minor gaps
- 0.9-1.0: Comprehensive, thorough coverage

Provide your score and reasoning.
```

### Citation Quality Evaluator

```
You are evaluating the citation quality in a research report.

<Generated Report>
{{output}}
</Generated Report>

Evaluate how well the report uses citations and sources.

Consider:
1. Are claims supported by citations?
2. Are citations placed appropriately (not just at end)?
3. Is there a good variety of sources?
4. Are the sources credible and relevant?

Score from 0 to 1:
- 0.0-0.3: Poor citation practices, unsupported claims
- 0.4-0.6: Some citations, inconsistent usage
- 0.7-0.8: Good citation practices, mostly supported
- 0.9-1.0: Excellent citations, all claims supported

Provide your score and reasoning.
```

---

## Configuration

Evaluators will be configured in Langfuse UI, not in code.

**Recommended settings:**

| Setting | Value | Rationale |
|---------|-------|-----------|
| Default model | `gpt-4o` | Best judgment quality |
| Sampling rate | 10-20% | Balance cost vs coverage |
| Scope | New traces only | Avoid reprocessing |
| Filter | `trace.name = "report_generation_v2"` | Target specific workflow |

---

## Cost Estimation

| Evaluator | Tokens/eval | Cost/eval | Monthly (100 reports, 10% sample) |
|-----------|-------------|-----------|-----------------------------------|
| Hallucination | ~2000 | ~$0.02 | $0.20 |
| Helpfulness | ~2000 | ~$0.02 | $0.20 |
| Report Depth | ~3000 | ~$0.03 | $0.30 |
| Citation Quality | ~2500 | ~$0.025 | $0.25 |

**Total estimated cost:** ~$1-2/month at 10% sampling

---

## References

- [Langfuse LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)
- [Langfuse Evaluator Library](https://langfuse.com/changelog/2025-05-24-langfuse-evaluator-library)
- [Custom Scores](https://langfuse.com/docs/evaluation/evaluation-methods/custom-scores)
- [Experiments via SDK](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk)
- [Datasets](https://langfuse.com/docs/evaluation/experiments/datasets)
- [External Evaluation Pipelines](https://langfuse.com/guides/cookbook/example_external_evaluation_pipelines)

---

## Next Steps

1. [ ] Set up LLM connection in Langfuse (if not already done)
2. [ ] Enable Hallucination + Helpfulness evaluators on production
3. [ ] Create custom Report Depth evaluator template
4. [ ] Create Langfuse dashboard for report quality metrics
5. [ ] Document evaluator configuration for team
