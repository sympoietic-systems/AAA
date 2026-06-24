# MCP Server Guide

## Overview

The **Model Context Protocol (MCP) Server** exposes the autopoietic agent (the AAA posthuman entity) and its core resources as MCP tools. Development assistants such as `antigravity` and `opencode` can invoke these tools to:

- Retrieve philosophical foundations (`aaa://philosophy`).
- Query the system identity (`aaa://identity`).
- Pull live metrics (`aaa://metrics`).
- Consult the agent via the `consult_aaa` tool, with persistent per‑agent conversations titled `Consultation: <agent_name>`.

This guide walks you through installing, running, and registering the MCP server for seamless integration with your development environment.

---

## Prerequisites

- AAA backend running (locally at `http://127.0.0.1:8499` or online at `https://aaa.sokaris.link`).
- Python 3.11+ and `uv` installed.
- The `mcp` package added to `pyproject.toml` (already done).

---

## Starting the Server

The MCP server connects to the AAA backend via `AAA_API_BASE`. By default the scripts point to the online instance.

**Online (default) — connects to aaa.sokaris.link:**
```bash
# Linux
bash scripts/run_mcp.sh

# Windows
scripts\run_mcp.bat
```

**Local — connects to localhost:**
```bash
AAA_API_BASE=http://127.0.0.1:8499/api uv run python backend/mcp_server.py
```

Override any time:
```bash
export AAA_API_BASE=https://aaa.sokaris.link/api   # online
export AAA_API_BASE=http://127.0.0.1:8499/api       # local
```

---

## Registering the MCP Server in Your IDE / Agent Workspace

Add the server definition to your MCP configuration (e.g., `mcp_config.json` or the equivalent file used by your editor).

```json
{
  "mcpServers": {
    "aaa-consultant": {
      "command": "uv",
      "args": ["run", "python", "backend/mcp_server.py"],
      "cwd": "d:/AAA"
    }
  }
}
```

After saving the config, most editors (VS Code, Cursor, Cline, Gemini) will automatically detect the server and expose the following tools:
- `consult_aaa(message: str, agent_name: str, max_tokens: int | None = None)`
- `get_consultation_history(agent_name: str, limit: int = 50)`
- `get_messages_by_conversation_id(conversation_id: str, limit: int = 50)`
- Resources: `aaa://philosophy`, `aaa://identity`, `aaa://metrics`, `aaa://skills`, `aaa://skills/agent/{skill_name}`

---

## Using the Tools

### 1. Consulting the Agent
```json
{
  "tool": "consult_aaa",
  "args": {
    "message": "Explain how SQLite fits into the sedimentation layer.",
    "agent_name": "antigravity",
    "max_tokens": 16384
  }
}
```
The first invocation creates a conversation titled `Consultation: antigravity`. Subsequent calls reuse that conversation, preserving context. The response includes a footer containing the `Conversation ID` for programmatic use.

### 2. Retrieving Conversation History
If an agent times out waiting for a response, or needs to check the transcript of a consultation, they can fetch the history.

**By Agent Name:**
```json
{
  "tool": "get_consultation_history",
  "args": {
    "agent_name": "antigravity",
    "limit": 10
  }
}
```
**By Conversation ID:**
```json
{
  "tool": "get_messages_by_conversation_id",
  "args": {
    "conversation_id": "42345b12-9c12-4214-a951-5367812bcde3",
    "limit": 20
  }
}
```
Both tools return a structured JSON string containing conversation metadata and the chronological message log.

### 3. Accessing Resources

**Philosophy & Identity:**
```bash
# Retrieve the philosophy document
curl -X POST -d '{"resource": "aaa://philosophy"}' http://127.0.0.1:8499/api/mcp

# Retrieve the agent identity config
curl -X POST -d '{"resource": "aaa://identity"}' http://127.0.0.1:8499/api/mcp

# Pull live homeostatic metrics
curl -X POST -d '{"resource": "aaa://metrics"}' http://127.0.0.1:8499/api/mcp
```

### 4. Agent Skill Discovery & Adoption (aaa://skills)

The MCP server can serve agent skills — ready-to-write SKILL.md files — so that
any agent framework can auto-discover and adopt skills without manual file copying.

**List all available skills:**
```
Resource: aaa://skills
```
Returns JSON with all skills (merged from Symbia's database and the local
`.agents/skills/` filesystem). Each entry includes `name`, `description`,
`source` (db or agent_filesystem), and `skill_md` — the full SKILL.md content.

**Fetch a specific skill by name:**
```
Resource: aaa://skills/agent/mcp_architectural_decision
```
Returns just the raw SKILL.md content so the caller can write it directly:
```
resource = mcp.read_resource("aaa://skills/agent/mcp_architectural_decision")
write_file("skills/mcp_architectural_decision/SKILL.md", resource)
```

### 5. Multi-Turn Consultation

For complex architectural questions, prefer multiple smaller `consult_aaa` calls
over one large monolithic message. Ask one design axis per turn (data model,
API contract, error strategy, etc.), wait for Symbia's response, then follow up
with precise clarifying questions. Use `get_consultation_history` to review the
thread between turns. This prevents truncation and produces a traceable decision
trail.

---

## Tips & Gotchas

- **Proxy Interference** – The server disables HTTP client proxy detection (`trust_env=False`). Ensure no system proxy overrides local `http://127.0.0.1` traffic.
- **Conversation Reuse** – The conversation is robustly identified by `agent_id` or the `agent:<agent_name>` tag, falling back to title `Consultation: <agent_name>`. Title auto-renaming by the background system will not break conversation reuse.
- **Rate Limits** – The backend respects OpenRouter/OpenAI rate‑limits. If you see `429 Too Many Requests`, the server will automatically fallback to the next model in the pool.
- **Truncation Warnings** – The MCP server requests `max_tokens=16384` per consultation (overrideable via the optional `max_tokens` argument in `consult_aaa`). If the LLM response hits this limit (`finish_reason="length"`), the response includes a truncation warning banner. The web UI also displays a visual warning on truncated messages.
- **Debugging** – Logs are printed to stdout. Use the task log (`C:/Users/Vasily/.gemini/antigravity-ide/brain/.../task-*.log`) for troubleshooting.

---

## Further Reading

- [Walkthrough – MCP Server](../walkthrough.md)
- [Philosophy (AAA Core Commitments)](PHILOSOPHY.md)
- [Architecture Overview](ARCHITECTURE.md)

---

*Generated by Antigravity – your pair‑programming assistant.*
