# ADR-058: Lightweight LLM-Driven Search Selection and Query Limits

**Date:** 2026-07-01  
**Status:** accepted  
**Deciders:** Antigravity, Symbia (consulted)  

---

## Context

During autonomous research iterations, two main issues caused high latency, excessive token usage, and dilution of source quality:
1. **Commercial SEO Noise:** Default search tool usage retrieved the top N results returned by search engines. These top positions are frequently occupied by SEO-optimized landing pages, advertisements, and low-fidelity mainstream summaries, bypassing academic publications, niche archives, and deep philosophical blog posts.
2. **Query Proliferation:** The planner step generated up to 9 search queries per iteration in an attempt to be thorough. Executing all queries sequentially or in parallel caused a high volume of web requests, consumed massive context budgets, and increased api token expenses dramatically.

---

## Decision

We implemented a lightweight LLM-driven filtering mechanism for web search results and safety query caps, backed by full env-var configurability:

### 1. High-Fidelity LLM Search Selector
In `backend/services/research/steps/search.py`:
- We now request a larger pool of search candidates (configurable default: 10 results).
- We pass this candidate pool (URL, title, and snippet) to a lightweight LLM call (`_select_high_fidelity_results`) using `generate_unified` with a minimal prompt, low temperature (`0.1`), and restricted max tokens (`500`).
- The selector prioritizes academic papers, primary source archives, and high-fidelity reporting, while explicitly filtering out commercial and shallow SEO content.
- If the LLM call fails or returns invalid selections, the step gracefully falls back to the top-ranked search engine results.

### 2. Query Proliferation Limits
In `backend/services/research/steps/plan.py` and `backend/prompts/research/orchestrator_planner.yaml`:
- Enforced a hard limit of maximum queries allowed per planning iteration (configurable default: 4 queries).
- The planner prompt is updated to advise the model to select the most relevant angles/queries and discard unimportant direct URLs.
- The backend checks the planner payload and truncates the query array to the configured maximum, preventing unexpected execution storms.

### 3. Declarative Environment Configurability
Unified these constraints into the core settings system:
- **`max_queries`** (mapped to `AAA_RESEARCH_MAX_QUERIES`, default: `4`): Caps the number of planned search queries.
- **`search_candidates`** (mapped to `AAA_RESEARCH_SEARCH_CANDIDATES`, default: `10`): Configures the candidate search pool size to fetch before LLM filtering.
- Defined default settings in `backend/config.yaml` and registered declarative overrides in `backend/config_schema.py` so they are fully modifiable via `.env`.

---

## Consequences

- **Quality Gain:** The research pipeline digests higher-quality, less commercialized sources, aligning with the philosophical depth of posthuman curation.
- **Resource Conservation:** Restricting planned queries to a maximum of 4 significantly reduces API latency, search tool limits, and token budgets.
- **Operability:** Administrators and operators can adjust the candidate pool size and query limit thresholds directly from `.env` without modifying Python code.
