# Configuration Reference

AAA is configured through two layers: `config.yaml` (defaults) and
environment variables (`.env` overrides). Env vars take precedence.

## config.yaml

```yaml
# ── Database ──────────────────────────────────────
database:
  path: "data/aaa.db"          # SQLite file (relative to backend/)

# ── Embeddings ────────────────────────────────────
embedding:
  model: "all-MiniLM-L6-v2"    # Any sentence-transformers model
  device: "cpu"                # cpu | cuda
  offline: true                # true: load from cache (no HF hub checks)
                               # false: always check HF hub for updates
                               # When offline=true and model not cached,
                               # it auto-downloads once, then stays offline.
  # cache_dir: ""              # optional: custom HuggingFace cache directory

# ── LLM Provider ─────────────────────────────────
llm:
  provider: "openrouter"       # openrouter | deepseek | openai_compatible
  model: ""                    # Leave empty → auto from provider
  api_base: ""                 # Leave empty → auto from provider
  thinking:
    enabled: false             # Chain-of-thought reasoning
    effort: "high"             # high | max (DeepSeek-v4 only)
  default_params:
    temperature: 0.7            # Ignored when thinking=enabled
    max_tokens: 2048

# ── Pipeline ─────────────────────────────────────
pipeline:
  modules:                     # Ordered processing stages
    - embedder
    - conversation_metrics
    - context_collector
    - sedimentation_retrieval
    - prompt_assembler
    - homeostatic_regulator
    - llm_client

# ── Personality ──────────────────────────────────
personality:
  path: "backend/personality/identity.yaml"   # Agent self-definition

# ── Context ──────────────────────────────────────
context:
  max_history: 20              # Fallback message count limit
  max_tokens: 16384            # Hard cap for entire context window

# ── Sedimentation ────────────────────────────────
sedimentation:
  enabled: true                # Cross-conversation retrieval
  sediment_token_budget: 2000  # Max tokens for cross-conversation messages
  sediment_count: 10           # Max number of sediment messages
  similarity_threshold: 0.3    # Minimum cosine similarity to include

# ── Homeostasis ──────────────────────────────────
homeostasis:
  pairwise_window: 5           # Prior human messages for similarity calc
  entropy_window: 5            # Window for rolling entropy
  agent_self_window: 5         # Prior agent messages for self-divergence

# ── Server ───────────────────────────────────────
server:
  host: "127.0.0.1"
  port: 8000

# ── Background Tasks ──────────────────────────────
# Models are tried in order. If one is rate-limited, the next is used.
# When all are exhausted, falls back to the fallback model.
background_llm:
  models:
    - "google/gemma-4-26b-a4b-it:free"
    - "nvidia/nemotron-nano-9b-v2:free"
    - "qwen/qwen3-next-80b-a3b-instruct:free"
  fallback_model: "openrouter/free"
  api_base: "https://openrouter.ai/api/v1"

# ── Vision Fallback ───────────────────────────────
vision_llm:
  model: "google/gemma-4-26b-a4b-it:free"
  api_base: "https://openrouter.ai/api/v1"
```

## Environment Variables

All env vars are optional overrides. Copy `.env.example` to `.env`.

### Provider Selection

| Variable | Values | Default |
|----------|--------|---------|
| `AAA_LLM_PROVIDER` | `openrouter`, `deepseek`, `openai_compatible` | `openrouter` |
| `AAA_LLM_MODEL` | Any model ID | Provider default |
| `AAA_LLM_API_BASE` | Full URL | Provider default |

### API Keys

| Variable | Provider | Get it from |
|----------|----------|-------------|
| `AAA_LLM_API_KEY` | openrouter | [openrouter.ai/keys](https://openrouter.ai/keys) |
| `AAA_DEEPSEEK_API_KEY` | deepseek | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) |

The correct key is automatically selected based on `AAA_LLM_PROVIDER`.

### Thinking Mode

| Variable | Values | Default |
|----------|--------|---------|
| `AAA_LLM_THINKING` | `true`, `false` | `false` |
| `AAA_LLM_REASONING_EFFORT` | `high`, `max` | `high` |

Only meaningful for DeepSeek-v4-pro/v4-flash. When enabled, `temperature`
and `top_p` are silently ignored by the model.

### Embedding

| Variable | Values | Default |
|----------|--------|---------|
| `AAA_EMBEDDING_MODEL` | Any sentence-transformers model | `all-MiniLM-L6-v2` |
| `AAA_EMBEDDING_DEVICE` | `cpu`, `cuda` | `cpu` |
| `AAA_EMBEDDING_OFFLINE` | `true`, `false` | `true` |
| `AAA_EMBEDDING_CACHE_DIR` | Path to cache directory | HuggingFace default |

When `offline=true` (default), the model loads from the local HuggingFace
cache without any network calls. If the model hasn't been downloaded yet,
it automatically fetches it once from HuggingFace and then uses the cache.
Set to `false` if you want the model to check for updates on every startup.

### Server

| Variable | Default |
|----------|---------|
| `AAA_SERVER_HOST` | `127.0.0.1` |
| `AAA_SERVER_PORT` | `8000` |

### Personality

| Variable | Default |
|----------|---------|
| `AAA_IDENTITY_PATH` | `backend/personality/identity.yaml` |

The identity file defines the agent's name, system prompt, traits, voice,
expertise, beliefs, and behaviors. The agent name drives the UI header
and is stored as `agent_id` in every database row for multi-agent support.

### Background Tasks

| Variable | Default | Description |
|----------|---------|-------------|
| `AAA_BACKGROUND_MODELS` | (from config.yaml) | Comma-separated model list, tried in order |
| `AAA_BACKGROUND_MODEL` | — | Single model (backward compat; `models` wins if both set) |
| `AAA_BACKGROUND_FALLBACK_MODEL` | `openrouter/free` | Model used when all pool models are rate-limited |
| `AAA_BACKGROUND_API_BASE` | `https://openrouter.ai/api/v1` | API base for background models |
| `AAA_BACKGROUND_API_KEY` | (inherits `AAA_LLM_API_KEY`) | Optional separate API key |

### Vision Fallback

| Variable | Default | Description |
|----------|---------|-------------|
| `AAA_VISION_MODEL` | `google/gemma-4-26b-a4b-it:free` | Vision-capable model for image processing |
| `AAA_VISION_API_BASE` | `https://openrouter.ai/api/v1` | API base for vision model |
| `AAA_VISION_API_KEY` | (inherits `AAA_LLM_API_KEY`) | Optional separate API key |

### Database

| Variable | Default |
|----------|---------|
| `AAA_DB_PATH` | `data/aaa.db` |

### Context & Sedimentation

| Variable | Values | Default |
|----------|--------|---------|
| `AAA_CONTEXT_MAX_TOKENS` | Any integer | `16384` (from `config.yaml`) |
| `AAA_SEDIMENT_TOKEN_BUDGET` | Any integer | `2000` (from `config.yaml`) |
| `AAA_SEDIMENT_COUNT` | Any integer | `10` (from `config.yaml`) |

## Provider Defaults

Without `AAA_LLM_MODEL` or `AAA_LLM_API_BASE` set, these auto-apply:

| `AAA_LLM_PROVIDER` | Default model | Default base URL |
|---|---|---|
| `openrouter` | `deepseek/deepseek-chat` | `https://openrouter.ai/api/v1` |
| `deepseek` | `deepseek-v4-pro` | `https://api.deepseek.com` |
| `openai_compatible` | `deepseek-v4-pro` | `https://api.deepseek.com` |

## Example Configurations

### OpenRouter with DeepSeek

```bash
# .env
AAA_LLM_PROVIDER=openrouter
AAA_LLM_API_KEY=sk-or-v1-abc123
```

Uses OpenRouter's `deepseek/deepseek-chat` by default.

### DeepSeek Direct with Thinking

```bash
# .env
AAA_LLM_PROVIDER=deepseek
AAA_DEEPSEEK_API_KEY=sk-abc123
AAA_LLM_THINKING=true
AAA_LLM_REASONING_EFFORT=high
```

Uses DeepSeek's `deepseek-v4-pro` with chain-of-thought.

### Custom Provider

```bash
# .env
AAA_LLM_PROVIDER=openai_compatible
AAA_LLM_API_KEY=sk-local-abc
AAA_LLM_MODEL=llama-3-8b
AAA_LLM_API_BASE=http://localhost:11434/v1
```

Points at a local Ollama or vLLM instance.

### Background Tasks Model Pool

```bash
# .env — prioritized model pool with fallback
AAA_BACKGROUND_MODELS=google/gemma-4-26b-a4b-it:free,nvidia/nemotron-nano-9b-v2:free
AAA_BACKGROUND_FALLBACK_MODEL=openrouter/free
AAA_BACKGROUND_API_BASE=https://openrouter.ai/api/v1
```

Models are tried in order. If one is rate-limited, the next is used.
When all are exhausted, falls back to `fallback_model`.

For a single model (backward compat):
```bash
# .env — single model
AAA_BACKGROUND_MODEL=google/gemma-4-26b-a4b-it:free
```

### Vision Model

```bash
# .env
AAA_VISION_MODEL=google/gemma-4-26b-a4b-it:free
AAA_VISION_API_BASE=https://openrouter.ai/api/v1
```

Independently configurable vision-capable model. When `use_vision: true` is
passed to the background endpoint, requests are routed to this model instead
of the background model.

### Background API

```bash
# Generate conversation title
curl -X POST http://localhost:8000/api/background \
  -H "Content-Type: application/json" \
  -d '{"action": "generate_title", "text": "Hello, I want to discuss..."}'

# Summarize text
curl -X POST http://localhost:8000/api/background \
  -H "Content-Type: application/json" \
  -d '{"action": "summarize", "text": "Long conversation text..."}'

# Consolidate memory
curl -X POST http://localhost:8000/api/background \
  -H "Content-Type: application/json" \
  -d '{"action": "consolidate", "context": {"messages": [...]}}'
```

See [ADR-006](decisions/ADR-006-background-tasks.md) for full design rationale.
