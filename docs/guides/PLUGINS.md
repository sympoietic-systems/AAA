# Plugin System

AAA uses a modular pipeline architecture. Every processing step is a
self-contained module implementing a shared interface. You can add,
remove, reorder, or replace modules without touching core code.

## Architecture

```
Pipeline:  [embedder] → [context_collector] → [llm_client]
              │              │                    │
              ▼              ▼                    ▼
         ProcessingModule  ProcessingModule   ProcessingModule
```

Each module receives a `payload` dict, enriches it, and passes it to
the next module. Modules are **stateless with respect to each other**
— they communicate only through the shared payload.

## ProcessingModule Interface

All modules must implement `backend.modules.base.ProcessingModule`:

```python
from backend.modules.base import ProcessingModule

class MyModule(ProcessingModule):

    @property
    def name(self) -> str:
        """Unique identifier used in config and registry."""
        return "my_module"

    def validate(self) -> bool:
        """Return True if module is ready to run (e.g., model loaded)."""
        return True

    async def process(self, payload: dict) -> dict:
        """Transform the payload. Must return the mutated dict."""
        return payload
```

### The Payload Contract

The payload dict is the shared data structure flowing through the pipeline.
Known keys (modules can add their own):

| Key | Type | Set by | Description |
|-----|------|--------|-------------|
| `content` | `str` | user input | Raw text from the user |
| `speaker` | `str` | user input | `"human"` or `"apparatus"` |
| `embedding` | `bytes` | embedder | Serialized float32 vector |
| `embedding_model` | `str` | embedder | e.g., `"all-MiniLM-L6-v2"` |
| `embedding_dim` | `int` | embedder | e.g., `384` |
| `messages` | `list[dict]` | context_collector | Formatted for LLM API |
| `response` | `str` | llm_client | The model's text output |
| `thinking` | `str \| None` | llm_client | Reasoning content (DeepSeek) |

## Creating a New Module

### Step 1 — Write the module

Create `backend/modules/sentiment.py`:

```python
from backend.modules.base import ProcessingModule

class SentimentModule(ProcessingModule):

    @property
    def name(self) -> str:
        return "sentiment"

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        content = payload.get("content", "")
        if "angry" in content.lower() or "frustrated" in content.lower():
            payload["sentiment"] = "negative"
        else:
            payload["sentiment"] = "neutral"
        return payload
```

### Step 2 — Register in the app lifespan

Open `backend/main.py`. In the `lifespan` function:

```python
from backend.modules.sentiment import SentimentModule

# After other module creation:
sentiment = SentimentModule()
registry.register("sentiment", lambda: sentiment)
```

### Step 3 — Add to the pipeline order

In `backend/config.yaml`:

```yaml
pipeline:
  modules:
    - embedder
    - sentiment          # ← added here, runs after embedding
    - context_collector
    - llm_client
```

### Step 4 — Restart the backend

```bash
uv run python -m backend.main
```

The new module is now part of every chat request.

## Module with Dependencies

If your module needs external services, accept them in `__init__`:

```python
class AnalyticsModule(ProcessingModule):
    def __init__(self, message_repo: MessageRepository):
        self._repo = message_repo

    @property
    def name(self) -> str:
        return "analytics"

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        total = len(self._repo.get_recent(limit=1000))
        payload["message_count"] = total
        return payload
```

Then in `main.py`, inject the dependency when registering:

```python
analytics = AnalyticsModule(message_repo=message_repo)
registry.register("analytics", lambda: analytics)
```

## Error Handling

Modules **should not** swallow exceptions. Let errors propagate —
the pipeline catches them, logs to the error database, and halts
processing. This ensures failures are visible and debuggable.

If you want to handle errors gracefully within a module:

```python
async def process(self, payload: dict) -> dict:
    try:
        payload["score"] = self._risky_operation()
    except Exception:
        payload["score"] = 0  # degrade gracefully
    return payload
```

## Best Practices

1. **Keep modules small** — one responsibility per module, ≤ 50 lines
2. **Be additive** — add keys to the payload, don't remove existing ones
3. **Stateless modules** — don't store mutable state between `process()` calls
4. **Lazy loading** — do heavy init in `validate()` or first `process()` call
5. **Configurable** — accept parameters via constructor, read from `config.yaml`
6. **Name convention** — module files are `snake_case.py`, class names are `PascalCaseModule`

## Extension Points (Phase 2–4)

| Phase | Module Idea | Input Key | Output Key |
|-------|------------|-----------|------------|
| **2** | `entropy_regulator` | `embedding` | modifies `llm_params` (temperature, penalty) |
| **3** | `sedimentation_engine` | `embedding` | `semantic_knots` (vector graph queries) |
| **4** | `belief_validator` | `response` | `schema_updates` (self-model mutation) |
