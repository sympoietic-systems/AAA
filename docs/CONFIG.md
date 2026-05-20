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
    - context_collector
    - prompt_assembler
    - llm_client

# ── Personality ──────────────────────────────────
personality:
  path: "backend/personality/identity.yaml"   # Agent self-definition

# ── Context ──────────────────────────────────────
context:
  max_history: 20              # Messages sent to LLM as context

# ── Server ───────────────────────────────────────
server:
  host: "127.0.0.1"
  port: 8000
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

### Database

| Variable | Default |
|----------|---------|
| `AAA_DB_PATH` | `data/aaa.db` |

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
