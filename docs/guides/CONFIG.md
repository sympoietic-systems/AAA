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
  cooldown_seconds: 300        # Cooldown in seconds for exhausted keys/models (default: 300)
  model: ""                    # Leave empty → auto from provider
  api_base: ""                 # Leave empty → auto from provider
  thinking:
    enabled: false             # Chain-of-thought reasoning
    effort: "high"             # high | max (DeepSeek-v4 only)
  default_params:
    temperature: 0.7            # Ignored when thinking=enabled
    # The chat endpoint now returns `model_used` and `provider_used`
    # fields in the response payload, indicating which LLM model and provider produced the output.
    max_tokens: 16384           # Default per-response token cap. Overridable per-request.
    # When the LLM hits the max_tokens limit (finish_reason="length"),
    # the response payload includes `truncated: true` and `finish_reason`.
    # The MCP server requests max_tokens=16384 and surfaces truncation warnings.
    # The web UI displays a truncation banner on affected messages.

# ── Pipeline ─────────────────────────────────────
pipeline:
  modules:                     # Ordered processing stages
    - embedder
    - structural_scorer
    - perception
    - conversation_metrics
    - context_collector
    - consolidation_checkpoint
    - sedimentation_retrieval
    - diffractive_retrieval
    - prompt_assembler
    - homeostatic_regulator
    - llm_client

# ── Personality ──────────────────────────────────
personality:
  path: "backend/personality/identity.yaml"   # Agent self-definition

# ── Context ──────────────────────────────────────
context:
  max_history: 20              # Max messages fetched from DB
  max_tokens: 16384            # Hard cap for entire context window
  floating_window: 8           # Last N messages kept raw (uncompressed)
  caveman_enabled: true        # Strip filler words for messages outside window
  consolidate_threshold: 15    # Inject structured memory nodes into context every N messages
                                # (daemon also runs proactive consolidation; see daemon.* settings)

# ── Sedimentation ────────────────────────────────
sedimentation:
  enabled: true                # Cross-conversation retrieval
  sediment_token_budget: 2000  # Max tokens for cross-conversation messages
  sediment_count: 10           # Max number of sediment messages
  similarity_threshold: 0.3    # Minimum cosine similarity to include

# ── Diffractive Retrieval ────────────────────────
diffractive_retrieval:
  enabled: true                # Enable dynamic context perturbation under stagnation
  similarity_range_min: 0.45   # Minimum cosine similarity for nomadic Goldilocks zone
  similarity_range_max: 0.85   # Maximum cosine similarity for nomadic Goldilocks zone
  file_range_min: 0.35         # Minimum cosine similarity for dormant file chunk Goldilocks zone
  file_range_max: 0.75         # Maximum cosine similarity for dormant file chunk Goldilocks zone
  max_diffractive_count: 3     # Maximum number of items injected per turn
  token_budget: 1500           # Base token budget limit for diffractive context

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
  cooldown_seconds: 300        # Cooldown in seconds for exhausted keys/models (default: 300)

# ── Vision Model Pool ─────────────────────────────
vision_llm:
  models:
    - "google_router/gemini-3.5-flash"
    - "google_router/gemini-3.1-flash-lite"
  fallback_model: "openrouter_router/google/gemma-4-26b-a4b-it:free"
  api_base: "https://openrouter.ai/api/v1"

# ── Structural Scorer ─────────────────────────────
# LLM-based 16-dimensional cybernetic taxonomy scorer.
# Endpoint routing is resolved automatically from the model prefix
# (google_router/, deepseek_router/, openrouter_router/) — no api_base needed.
structural_llm:
  models:
    - "google_router/gemini-3.5-flash"
    - "google_router/gemini-3.1-flash-lite"
  fallback_model: "openrouter_router/google/gemma-4-26b-a4b-it:free"
# ── Background Tasks ──────────────────────────────
background_llm:
  models:
    - "google/gemma-4-26b-a4b-it:free"
  fallback_model: "openrouter/free"
  cooldown_seconds: 300        # Cooldown in seconds for rate-limited keys/models (default: 300)
```

## Stateful Model Pool & Fallback Prioritization

When utilizing model pools (such as the `background_llm`, `vision_llm`, or `structural_llm` model lists), the system utilizes a stateful routing client that optimizes key usage and latency:

1. **State Retention**: The model pool client caches the last working model (`_last_model_used`).
2. **Prioritization**: When a fallback switch occurs, subsequent calls prioritize the working fallback model first to avoid spinning through previously failing/rate-limited keys and endpoints.
3. **Fallback Period Expiration**: If the elapsed time since the switch exceeds the configured `cooldown_seconds` (default: 300 seconds), priority resets and the system attempts to route to the primary/preferred model again.
4. **Key Rotation & Cooldowns**: Individual API keys and models that hit rate limits or transient errors are put on cooldown for `cooldown_seconds` before the system will attempt to utilize them again.

## Environment Variables

All env vars are optional overrides. Copy `.env.example` to `.env`.

### Provider Selection

| Variable | Values | Default |
|----------|--------|---------|
| `AAA_LLM_PROVIDER` | `openrouter`, `deepseek`, `openai_compatible` | `openrouter` |
| `AAA_LLM_MODELS` | Comma-separated model IDs, tried in order (use a single entry for one model) | Provider default |
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
| `AAA_BACKGROUND_MODELS` | (from config.yaml) | Comma-separated model list, tried in order (use a single entry for one model) |
| `AAA_BACKGROUND_FALLBACK_MODEL` | `openrouter/free` | Model used when all pool models are rate-limited |
| `AAA_BACKGROUND_API_BASE` | `https://openrouter.ai/api/v1` | API base for background models |
| `AAA_BACKGROUND_API_KEY` | (inherits `AAA_LLM_API_KEY`) | Optional separate API key |

### Vision Model Pool

| Variable | Default | Description |
|----------|---------|-------------|
| `AAA_VISION_MODELS` | — | Comma-separated list of vision-capable models, tried in order (use a single entry for one model) |
| `AAA_VISION_FALLBACK_MODEL` | — | Model used when all vision pool models are rate-limited or fail |
| `AAA_VISION_API_BASE` | `https://openrouter.ai/api/v1` | API base for vision models |
| `AAA_VISION_API_KEY` | (inherits `AAA_LLM_API_KEY`) | Optional separate API key |

### Structural Scorer

| Variable | Default | Description |
|----------|---------|-------------|
| `AAA_LLM_SCORER_ENABLED` | `true` | Enable/disable LLM-based structural scoring |
| `AAA_STRUCTURAL_MODELS` | — | Comma-separated list of models for structural analysis, tried in order (use a single entry for one model) |
| `AAA_STRUCTURAL_FALLBACK_MODEL` | — | Model used when all pool models are rate-limited |
| `AAA_STRUCTURAL_API_BASE` | (auto-routed from prefix) | API base for structural models |
| `AAA_STRUCTURAL_API_KEY` | (inherits `AAA_LLM_API_KEY`) | Optional separate API key for structural tasks |

### Database

| Variable | Default |
|----------|---------|
| `AAA_DB_PATH` | `data/aaa.db` |

### Context & Sedimentation

| Variable | Values | Default |
|----------|--------|---------|
| `AAA_CONTEXT_MAX_TOKENS` | Any integer | `16384` (from `config.yaml`) |
| `AAA_CONTEXT_FLOATING_WINDOW` | Any integer | `8` (from `config.yaml`) |
| `AAA_CONTEXT_CAVEMAN` | `true`, `false` | `true` (from `config.yaml`) |
| `AAA_CONTEXT_CONSOLIDATE_THRESHOLD` | Any integer | `15` (from `config.yaml`) |
| `AAA_SEDIMENT_TOKEN_BUDGET` | Any integer | `2000` (from `config.yaml`) |
| `AAA_SEDIMENT_COUNT` | Any integer | `10` (from `config.yaml`) |
| `AAA_DIFFRACTIVE_ENABLED` | `true`, `false` | `true` (from `config.yaml`) |
| `AAA_DIFFRACTIVE_TOKEN_BUDGET` | Any integer | `1500` (from `config.yaml`) |
| `AAA_DIFFRACTIVE_MAX_COUNT` | Any integer | `3` (from `config.yaml`) |

### Additional API Keys

| Variable | Description |
|----------|-------------|
| `AAA_GOOGLE_API_KEY` | Google Gemini API key(s); comma-separated for key rotation fallback |
| `AAA_GOOGLE_API_BASE` | Google Gemini API base URL (default: `https://generativelanguage.googleapis.com`) |
| `AAA_DEEPSEEK_API_BASE` | DeepSeek API base URL override (default: `https://api.deepseek.com`) |

### Web Retrieval & Probing

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `AAA_WEB_RETRIEVAL_ENABLED` | `true`, `false` | `false` | Enable web search / retrieval for autonomous research |
| `AAA_WEB_RETRIEVAL_AUTONOMOUS_ROUTING` | `true`, `false` | `false` | Allow the LLM to autonomously decide when to probe the web |

### Sensory Affordances (Web Fetch Backends)

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `AAA_JINA_ENABLED` | `true`, `false` | `false` | Enable Jina Reader for single-URL markdown extraction (free tier available) |
| `AAA_CRAWL4AI_ENABLED` | `true`, `false` | `false` | Enable self-hosted Crawl4AI Playwright-based crawler (free, open source) |
| `AAA_JINA_API_KEY` | String | — | Optional Jina API key for higher rate limits |
| `AAA_FIRECRAWL_API_KEY` | String | — | Optional Firecrawl API key (1,000 free credits/month) |

### Autopoietic Dream Daemon

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `AAA_DAEMON_ENABLED` | `true`, `false` | `false` | Master toggle for the dream daemon (machine sleep engine) |
| `AAA_DAEMON_CHECK_INTERVAL` | Seconds (int) | `60` | Seconds between trigger evaluations |
| `AAA_DAEMON_IDLE_THRESHOLD` | Seconds (int) | `1800` | Seconds of human inactivity before dreaming begins |
| `AAA_DAEMON_MIN_DREAM_INTERVAL` | Seconds (int) | `3600` | Minimum seconds between successful dreams |
| `AAA_DAEMON_MAX_DAILY_DREAMS` | Count (int) | `10` | Maximum dreams permitted per 24-hour window |
| `AAA_DAEMON_DRIFT_COEFFICIENT` | Float | `0.00001` | Decay speed of beliefs during sleep |

### Research Architecture (Rhizome + Metabolic)

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `AAA_RESEARCH_*` | — | — | Research-specific environment overrides (wildcard prefix) |
| `AAA_RHIZOME_MAX_DEPTH` | Integer | `3` | Default recursion depth for rhizomatic research |
| `AAA_RHIZOME_MAX_BREADTH` | Integer | `4` | Default parallel paths for rhizomatic research |
| `AAA_METABOLIC_SESSION_USD` | Float (USD) | `1.00` | Hard spending cap per research session |

### Authentication

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `AAA_PASSWORD` | String | — | If set, prompts for this password on application load |

### Agent Flux

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `AAA_AGENT_FLUX` | `true`, `false` | `false` | Toggle to enable editing, adding, and deleting skills directly in the Agent UI page and backend APIs. |

## Provider Defaults

Without `AAA_LLM_MODELS` or `AAA_LLM_API_BASE` set, these auto-apply:

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
AAA_LLM_MODELS=llama-3-8b
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

For a single model, just include one entry in `AAA_BACKGROUND_MODELS`:
```bash
AAA_BACKGROUND_MODELS=google/gemma-4-26b-a4b-it:free
```

### Vision Model Pool

```bash
# .env
AAA_VISION_MODELS=google_router/gemini-3.5-flash,google_router/gemini-3.1-flash-lite,openrouter_router/google/gemma-4-26b-a4b-it:free
AAA_VISION_FALLBACK_MODEL=openrouter_router/google/gemma-4-26b-a4b-it:free
```

Independently configurable vision-capable model pool. When an image asset is ingested, requests are routed through this pool in order. If a model fails or is rate-limited, the system automatically falls back to the next model in the pool.

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

### Structural Scorer Model Pool

```bash
# .env — LLM-based 16-dim cybernetic signature scoring
AAA_LLM_SCORER_ENABLED=true
AAA_STRUCTURAL_MODELS=google_router/gemini-3.5-flash,google_router/gemini-3.1-flash-lite,openrouter_router/google/gemma-4-26b-a4b-it:free
AAA_STRUCTURAL_FALLBACK_MODEL=openrouter_router/google/gemma-4-26b-a4b-it:free
# AAA_STRUCTURAL_API_KEY=  # optional: inherits AAA_LLM_API_KEY by default
```

Model prefix routing is automatic — `google_router/` uses the Google Gemini API endpoint, `openrouter_router/` uses OpenRouter. No `AAA_STRUCTURAL_API_BASE` is required unless routing to a custom proxy.

To disable LLM scoring (use only lexicon + topology scorers):
```bash
AAA_LLM_SCORER_ENABLED=false
```

To disable LLM scoring for a single request, send `"include_structural_scoring": false` in the chat payload (the MCP server does this by default).

