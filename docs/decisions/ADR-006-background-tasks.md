# ADR-006: Background Tasks — Autopoietic Self-Maintenance

**Date:** 2026-05-21
**Status:** accepted
**Deciders:** Vector, aaa project

## Context

The agent performs several self-maintenance operations that are conceptually
distinct from the live conversation pipeline:

1. **Conversation naming** — generating identity markers for new encounters
2. **Text summarization** — distilling structural residue from traces
3. **Memory consolidation** — sedimentation: transforming raw episodic memory
   into structural nodes that exert gravity on future retrievals

These operations were previously handled inline (e.g., `_generate_title()` in
`routes.py`) using the primary conversation model. This created several problems:

- **Resource contention**: Background operations blocked the chat response
- **Model mismatch**: The primary model (e.g., DeepSeek-v4-pro) is optimized
  for conversation, not for lightweight maintenance tasks
- **No vision fallback**: No mechanism to route image-based requests to a
  vision-capable model when the primary model lacks vision support
- **Not extensible**: Adding new self-maintenance operations required modifying
  route handlers directly

In AAA's framework, these are **autopoietic processes** — the system tending
to its own cognitive substrate. They should be:
- Independently configurable (separate model)
- Extensible (new actions without touching the pipeline)
- Resilient (rate limit handling, retries)
- Model-agnostic (work with both thinking and non-thinking models)

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Inline in routes** | Simple; no new infrastructure | Blocks chat; not extensible; mixes concerns |
| **Background job queue (Celery/RQ)** | Proper async; scalable | Heavy infrastructure; overkill for current needs |
| **Dedicated endpoint + engine** | Clean separation; extensible; testable | Requires new module structure |
| **Pipeline integration** | Consistent with existing architecture | Background tasks are not part of the conversation flow; would complicate pipeline |

## Decision

**Dedicated endpoint + action engine with separate model configuration.**

Rationale:
- Background tasks are **not** part of the conversation pipeline — they are
  self-maintenance operations that can be triggered independently
- A dedicated `POST /api/background` endpoint provides a clean API surface
- The `BackgroundTaskEngine` with pluggable `BackgroundAction` classes enables
  adding new operations without modifying existing code
- Separate model configuration (`background_llm`, `vision_llm`) allows
  optimizing for cost/speed independently from the conversation model

### Architecture

```
backend/modules/background_tasks/
    base.py          # BackgroundAction abstract class
    engine.py        # BackgroundTaskEngine — dispatches to actions
    actions/
        title.py       # GenerateTitleAction
        summarize.py   # SummarizeAction
        consolidate.py # ConsolidateAction
```

### Action Interface

```python
class BackgroundAction(ABC):
    @property
    @abstractmethod
    def action_type(self) -> str: ...

    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict: ...
```

Each action defines its own system prompt (philosophically aligned) and
execution logic. The engine routes to the correct action by `action_type`.

### Model Configuration

Two new model sections in `config.yaml`, independently configurable:

```yaml
background_llm:
  model: "google/gemma-4-26b-a4b-it:free"
  api_base: "https://openrouter.ai/api/v1"

vision_llm:
  model: "google/gemma-4-26b-a4b-it:free"
  api_base: "https://openrouter.ai/api/v1"
```

Environment variable overrides:
- `AAA_BACKGROUND_MODEL`, `AAA_BACKGROUND_API_BASE`
- `AAA_VISION_MODEL`, `AAA_VISION_API_BASE`
- Optional separate keys: `AAA_BACKGROUND_API_KEY`, `AAA_VISION_API_KEY`

If not overridden, background/vision models inherit the primary LLM API key.

### Response Format (Consistent)

The `OpenAICompatibleProvider._parse_message()` method normalizes responses
from all model types into a consistent format:

```python
{
    "content": "actual response text",      # Always a string
    "reasoning": "thinking trace if any",    # From reasoning models
    "thinking": "same as reasoning",         # For compatibility
    "model": "model identifier",             # Actual model used
    "raw_message": {...},                    # Full message dict
}
```

This handles:
- **Non-thinking models**: `content` has the response, `reasoning` is empty
- **Thinking models** (DeepSeek): `content` has the answer, `reasoning_content`
  has the trace
- **OpenRouter free models** (various formats): `reasoning` may come from
  `reasoning`, `reasoning_details` array, or `content` may be null
- **Reasoning models with no final answer**: `content` falls back to reasoning

### Rate Limit Handling

`OpenAICompatibleProvider` implements exponential backoff retry logic:

- Max retries: 3 (configurable via `max_retries`)
- Backoff: 1s → 2s → 4s → 8s (capped at 30s)
- Parses `x-ratelimit-*` headers from OpenRouter responses
- Raises `RateLimitError` with remaining quota info when exhausted
- `BackgroundTaskEngine` catches `RateLimitError` and returns graceful error
  response instead of crashing

### API Endpoint

```
POST /api/background
{
    "action": "generate_title" | "summarize" | "consolidate",
    "text": "...",                    # For summarize
    "conversation_id": "...",         # Optional
    "context": {"messages": [...]},   # For consolidate/title
    "use_vision": false               # Route to vision provider
}
```

Response:
```json
{
    "action": "generate_title",
    "result": "Quantum Consciousness Dialogue",
    "model_used": "google/gemma-4-26b-a4b-it:free",
    "error": null
}
```

### Title Extraction

The `GenerateTitleAction._extract_title()` method handles output from both
thinking and non-thinking models:

1. Split by newlines — reasoning models often separate thinking from answer
2. Look for last line that looks like a title (2-8 words)
3. Strip reasoning patterns (self-talk, meta-commentary, thinking markers)
4. Split by sentence terminators, try last part first
5. Fallback to first 6 meaningful words, then to input text

This ensures the action doesn't crash when the model changes.

### Integration with Chat Pipeline

The existing `_generate_title()` call in the chat endpoint now delegates to
`BackgroundTaskEngine.run("generate_title", ...)`. The chat endpoint still
waits synchronously for the title (minimal latency for 30-token call), but
uses the background model instead of the primary conversation model.

## Consequences

**Easier:**
- Background operations use a model optimized for cost/speed
- New actions can be added by creating a new file in `actions/`
- Rate limit handling is centralized in the provider
- Vision model can be swapped independently
- Consistent response format regardless of model type

**Harder:**
- Two additional model configurations to maintain
- `openrouter/free` router picks random models with varying output formats
- Free tier has rate limits (50 req/day, 20 req/min)
- Title extraction requires heuristics to handle reasoning model output

## Future Work

### Pipeline Integration
Background tasks could be triggered automatically by the pipeline:
- After a new conversation reaches N messages → auto-generate title
- After a conversation ends → auto-consolidate memory
- Periodic background consolidation of old conversations

### Async Task Queue
For heavy operations (consolidating long conversations), a proper async
queue (asyncio task pool or lightweight scheduler) would prevent blocking
the API response.

### Vision Perception
When the primary model lacks vision support, uploaded images can be routed
to the `vision_llm` for description, then stored as text sediment in
`perception_sediment`.

### Action Cost Tracking
Each action could track token usage and cost, surfaced in the API response
for monitoring.

### Scheduled Consolidation
A background scheduler could run consolidation on idle conversations
periodically, building the agent's memory graph without user intervention.
