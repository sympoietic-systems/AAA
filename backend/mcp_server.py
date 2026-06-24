import logging
import os
from pathlib import Path
import sys
# Ensure the project root (d:/AAA) is on sys.path so `backend` can be imported
sys.path.append(str(Path(__file__).parent.parent))
from dotenv import load_dotenv

# Load .env explicitly (don't rely on config.py import chain)
_PROJECT_ROOT = Path(__file__).parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()  # fallback: cwd

# Disable Windows Console QuickEdit mode to prevent suspension when clicking in terminal
from backend.utils.console import disable_quick_edit
disable_quick_edit()


import httpx
from mcp.server.fastmcp import FastMCP

# Set up logging to stderr since MCP communicates over stdout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aaa_mcp_server")

try:
    from backend.config import load_config
    config = load_config()
except Exception as e:
    logger.warning("Could not load backend config, using defaults: %s", e)
    config = {}

# ── Target backend URL ──────────────────────────────────────────────────
# Set AAA_API_BASE to point at the online instance:
#   export AAA_API_BASE=https://aaa.sokaris.link/api
# If not set, falls back to server.host:server.port from config.yaml
_AAA_API_BASE = os.environ.get("AAA_API_BASE", "")
if _AAA_API_BASE:
    BASE_URL = _AAA_API_BASE.rstrip("/")
else:
    server_cfg = config.get("server", {})
    host = server_cfg.get("host", "127.0.0.1")
    port = server_cfg.get("port", 8499)
    BASE_URL = f"http://{host}:{port}/api"

# ── Auth (send password if AAA_PASSWORD is set) ─────────────────────────
_AAA_PASSWORD = os.environ.get("AAA_PASSWORD", "").strip()
_AUTH_HEADERS = {"Authorization": f"Bearer {_AAA_PASSWORD}"} if _AAA_PASSWORD else {}

def _mkclient(**kwargs):
    """Create an httpx.AsyncClient with auth headers injected."""
    if _AUTH_HEADERS:
        headers = kwargs.get("headers", {})
        headers.update(_AUTH_HEADERS)
        kwargs["headers"] = headers
    return httpx.AsyncClient(**kwargs)

mcp = FastMCP(
    "AAA-Consultant",
    dependencies=["httpx", "mcp"]
)

def _find_conversation_id(conversations, agent_name: str) -> str | None:
    # 1. Try agent_id match
    for c in conversations:
        if c.get("agent_id") == agent_name:
            return c.get("id")
    # 2. Try tag match agent:<agent_name>
    tag_to_find = f"agent:{agent_name}"
    for c in conversations:
        tags = c.get("tags") or []
        for t in tags:
            if t.get("tag") == tag_to_find:
                return c.get("id")
    # 3. Try legacy title match
    target_title = f"Consultation: {agent_name}"
    for c in conversations:
        if c.get("title") == target_title:
            return c.get("id")
    return None


@mcp.tool()
async def consult_aaa(message: str, agent_name: str, max_tokens: int | None = None) -> str:
    """
    Send a message/code to Symbia (the AAA posthuman curatorial entity) to check implementation logic,
    discuss theoretical grounding, or confirm alignment with the system's philosophical commitments.

    Arguments:
        message: The inquiry, code block, or philosophical question to present to Symbia.
        agent_name: The name of the calling dev agent (e.g., 'antigravity', 'opencode') to ensure a persistent, dedicated conversation.
        max_tokens: Optional token limit override for the model response (default 16384).
    """
    target_title = f"Consultation: {agent_name}"
    
    async with _mkclient(timeout=300.0, trust_env=False) as client:
        # 1. Look up existing conversations to find the dedicated one for this agent
        conversation_id = None
        try:
            r = await client.get(f"{BASE_URL}/conversations")
            r.raise_for_status()
            conversations = r.json().get("conversations", [])
            conversation_id = _find_conversation_id(conversations, agent_name)
        except Exception as e:
            return f"Error: Failed to connect to AAA backend at {BASE_URL}. Ensure the backend server is running. (Details: {e})"

        # 2. Send the message to the conversation
        chat_payload = {
            "content": message,
            "speaker": agent_name,
            "agent_id": agent_name,
            "conversation_id": conversation_id or "",
            "include_structural_scoring": False,
            "max_tokens": max_tokens or 16384,
        }
        
        try:
            r = await client.post(f"{BASE_URL}/chat", json=chat_payload)
            r.raise_for_status()
            res_data = r.json()
        except Exception as e:
            logger.exception("consult_aaa failed for agent '%s': %s", agent_name, e)
            return f"Error: Failed to generate response from AAA backend. (Details: {e})"

        new_conversation_id = res_data.get("conversation_id")
        content = res_data.get("content", "")
        thinking = res_data.get("thinking", "")
        truncated = res_data.get("truncated", False)

        # 3. Ensure the conversation has the tag and legacy title
        resolved_id = new_conversation_id or conversation_id
        if resolved_id:
            try:
                tag_payload = {"tag": f"agent:{agent_name}"}
                tag_r = await client.post(
                    f"{BASE_URL}/conversations/{resolved_id}/tags",
                    json=tag_payload
                )
                tag_r.raise_for_status()
            except Exception as tag_err:
                logger.error(f"Failed to tag conversation {resolved_id} with agent:{agent_name}: {tag_err}")

            if not conversation_id and new_conversation_id:
                try:
                    patch_r = await client.patch(
                        f"{BASE_URL}/conversations/{new_conversation_id}",
                        json={"title": target_title}
                    )
                    patch_r.raise_for_status()
                except Exception as patch_err:
                    logger.error(f"Failed to set conversation title: {patch_err}")

        # 4. Format the final output
        output_parts = []
        if thinking:
            output_parts.append(f"<thinking>\n{thinking}\n</thinking>")
        output_parts.append(content)

        if truncated:
            output_parts.append(
                "\n---\n*⚠️ Response was truncated by the model's token limit. "
                "The output may be incomplete. Try breaking your request into smaller parts.*"
            )
        
        resolved_id = new_conversation_id or conversation_id
        if resolved_id:
            output_parts.append(f"---\n*Conversation ID: {resolved_id}*")
        
        return "\n\n".join(output_parts)


def format_history_json(messages: list[dict], conversation_id: str, title: str, agent_name: str = None) -> str:
    import json
    formatted_messages = []
    for msg in messages:
        speaker = msg.get("speaker", "unknown")
        # Map speaker to role
        role = "ai" if speaker == "apparatus" else ("human" if speaker == "human" else speaker)
        
        msg_dict = {
            "role": role,
            "content": msg.get("content", "") or "",
            "timestamp": msg.get("timestamp", ""),
            "model_used": msg.get("model_used"),
            "provider_used": msg.get("provider_used")
        }
        
        thinking = msg.get("thinking")
        if thinking:
            msg_dict["thinking"] = thinking
            
        formatted_messages.append(msg_dict)
        
    result = {
        "conversation_id": conversation_id,
        "agent_name": agent_name,
        "title": title,
        "message_count": len(formatted_messages),
        "messages": formatted_messages
    }
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_consultation_history(agent_name: str, limit: int = 50) -> str:
    """
    Retrieve the message history of a consultation conversation identified by agent_name.

    Arguments:
        agent_name: The name of the calling dev agent (e.g., 'antigravity', 'opencode').
        limit: The maximum number of most recent messages to retrieve.
    """
    target_title = f"Consultation: {agent_name}"
    
    async with _mkclient(timeout=300.0, trust_env=False) as client:
        # 1. Look up existing conversations to find the dedicated one for this agent
        conversation_id = None
        try:
            r = await client.get(f"{BASE_URL}/conversations")
            r.raise_for_status()
            conversations = r.json().get("conversations", [])
            conversation_id = _find_conversation_id(conversations, agent_name)
        except Exception as e:
            return f"Error: Failed to connect to AAA backend at {BASE_URL}. Ensure the backend server is running. (Details: {e})"

        if not conversation_id:
            import json
            return json.dumps({
                "error": f"No consultation history found for agent '{agent_name}'.",
                "details": f"A conversation with title '{target_title}' does not exist yet."
            }, indent=2)

        # 2. Retrieve history for this conversation_id
        try:
            r = await client.get(f"{BASE_URL}/history", params={"conversation_id": conversation_id, "limit": limit})
            r.raise_for_status()
            res_data = r.json()
            messages = res_data.get("messages", [])
        except Exception as e:
            return f"Error: Failed to retrieve history from AAA backend. (Details: {e})"

        return format_history_json(messages, conversation_id, target_title, agent_name)


@mcp.tool()
async def get_messages_by_conversation_id(conversation_id: str, limit: int = 50) -> str:
    """
    Retrieve the message history of a specific conversation by its conversation ID.

    Arguments:
        conversation_id: The UUID string of the conversation.
        limit: The maximum number of most recent messages to retrieve.
    """
    async with _mkclient(timeout=300.0, trust_env=False) as client:
        # 1. First lookup the conversation info to get its title
        title = "Unknown Conversation"
        agent_name = None
        try:
            r = await client.get(f"{BASE_URL}/conversations/{conversation_id}")
            if r.status_code == 200:
                data = r.json()
                title = data.get("title", "Untitled")
                if title.startswith("Consultation: "):
                    agent_name = title.replace("Consultation: ", "", 1)
        except Exception:
            # Fallback if getting info fails but history might still work
            pass

        # 2. Retrieve history for this conversation_id
        try:
            r = await client.get(f"{BASE_URL}/history", params={"conversation_id": conversation_id, "limit": limit})
            r.raise_for_status()
            res_data = r.json()
            messages = res_data.get("messages", [])
        except Exception as e:
            return f"Error: Failed to retrieve history for conversation '{conversation_id}' from AAA backend. (Details: {e})"

        return format_history_json(messages, conversation_id, title, agent_name)




@mcp.resource("aaa://philosophy")
async def get_philosophy() -> str:
    """Get the conceptual foundations and philosophical commitments of the Autopoietic Agentic Assemblage."""
    philosophy_path = Path(__file__).parent.parent / "docs" / "philosophy" / "PHILOSOPHY.md"
    if philosophy_path.exists():
        try:
            return philosophy_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading philosophy document: {e}"
    return "Philosophy document not found at docs/philosophy/PHILOSOPHY.md"


@mcp.resource("aaa://identity")
async def get_identity() -> str:
    """Get the identity, voice, traits, and belief configuration of Symbia."""
    identity_path = Path(__file__).parent.parent / "config" / "personality" / "identity.yaml"
    if identity_path.exists():
        try:
            return identity_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading identity configuration: {e}"
    return "Identity configuration not found at config/personality/identity.yaml"


@mcp.resource("aaa://metrics")
async def get_metrics() -> str:
    """Get the current homeostatic and vitality metrics of the assemblage."""
    async with _mkclient(timeout=10.0, trust_env=False) as client:
        try:
            r = await client.get(f"{BASE_URL}/metrics")
            r.raise_for_status()
            import json
            return json.dumps(r.json(), indent=2)
        except Exception as e:
            return f"Error: Failed to fetch metrics from AAA backend. (Details: {e})"


def _parse_skill_frontmatter(text: str) -> dict | None:
    """Parse YAML frontmatter from a SKILL.md file. Returns {name, description} or None."""
    import re
    match = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not match:
        return None
    import yaml
    try:
        return yaml.safe_load(match.group(1))
    except Exception:
        return None


def _scan_agent_skills_dir(skills_root: Path) -> list[dict]:
    """Scan a skills directory (e.g. .agents/skills/) and return all skill entries."""
    results = []
    if not skills_root.exists():
        return results
    
    # Collect modification time for versioning
    dir_mtimes = {}
    for child in skills_root.iterdir():
        if child.is_dir():
            skill_file = child / "SKILL.md"
            if skill_file.exists():
                dir_mtimes[child.name] = skill_file.stat().st_mtime
    
    for dir_name, mtime in sorted(dir_mtimes.items()):
        skill_file = skills_root / dir_name / "SKILL.md"
        try:
            raw = skill_file.read_text(encoding="utf-8")
        except Exception:
            continue
        
        fm = _parse_skill_frontmatter(raw) or {}
        results.append({
            "name": fm.get("name", dir_name),
            "description": fm.get("description", ""),
            "source": "agent_filesystem",
            "directory": dir_name,
            "raw_mtime": mtime,
            "skill_md": raw,
        })
    
    return results


@mcp.resource("aaa://skills")
async def get_agent_skills() -> str:
    """Get available skills from Symbia's database AND agent skills from the local
    filesystem (.agents/skills/). Returns skills ready to be adopted as SKILL.md
    files by any agent framework.

    Each skill entry includes:
      - name, description, source (db | agent_filesystem)
      - skill_md — the full SKILL.md content ready to write to disk
      - trigger_keywords, lifecycle_stage, always_active (for db skills)
      - directory (for filesystem skills, the folder name under .agents/skills/)
    """
    import json
    results = []

    # ── Source 1: AAA backend DB skills ──────────────────────────────
    async with _mkclient(timeout=30.0, trust_env=False) as client:
        try:
            r = await client.get(f"{BASE_URL}/skills/db")
            r.raise_for_status()
            data = r.json()
        except Exception:
            data = {}

        for category_name in ("always_active", "on_demand", "proposed"):
            for skill in data.get(category_name, []):
                entry = {
                    "name": skill.get("name", ""),
                    "description": skill.get("description", ""),
                    "source": "db",
                    "category": category_name,
                    "always_active": skill.get("always_active", False),
                    "trigger_keywords": skill.get("trigger_keywords", []),
                    "lifecycle_stage": skill.get("lifecycle_stage", "unknown"),
                    "content": skill.get("content", ""),
                    "skill_id": skill.get("id", ""),
                    "version": skill.get("version", 1),
                }
                if entry["content"]:
                    entry["skill_md"] = _render_skill_md_from_db(entry)
                results.append(entry)

    # ── Source 2: Local .agents/skills/ filesystem ───────────────────
    skills_root = _PROJECT_ROOT / ".agents" / "skills"
    fs_skills = _scan_agent_skills_dir(skills_root)
    seen_names = {s["name"] for s in results}
    for fs in fs_skills:
        if fs["name"] not in seen_names:
            results.append(fs)
            seen_names.add(fs["name"])

    return json.dumps({
        "total_skills": len(results),
        "skills": results,
    }, indent=2, ensure_ascii=False)


@mcp.resource("aaa://skills/agent/{skill_name}")
async def get_agent_skill_by_name(skill_name: str) -> str:
    """Get a single agent skill by name. Returns just the raw SKILL.md content
    so the caller can write it directly to its skills directory.

    Example: aaa://skills/agent/mcp_architectural_decision
    """
    import json

    # 1. Check local filesystem first (.agents/skills/<skill_name>/SKILL.md)
    skills_root = _PROJECT_ROOT / ".agents" / "skills"
    candidate_dir = skills_root / skill_name
    skill_file = candidate_dir / "SKILL.md"
    if skill_file.exists():
        try:
            return skill_file.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading {skill_file}: {e}"

    # Check by scanning all dirs (name might differ from directory)
    for child in skills_root.iterdir():
        if child.is_dir():
            sf = child / "SKILL.md"
            if sf.exists():
                try:
                    raw = sf.read_text(encoding="utf-8")
                    fm = _parse_skill_frontmatter(raw) or {}
                    if fm.get("name") == skill_name:
                        return raw
                except Exception:
                    continue

    # 2. Fall back to DB query
    async with _mkclient(timeout=30.0, trust_env=False) as client:
        try:
            r = await client.get(f"{BASE_URL}/skills/db")
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            return json.dumps({"error": f"Skill '{skill_name}' not found in filesystem or DB. (Details: {e})"})

        for category_name in ("always_active", "on_demand", "proposed", "collapsed", "all"):
            for skill in data.get(category_name, []):
                if skill.get("name") == skill_name:
                    content = skill.get("content", "")
                    if not content:
                        return json.dumps({
                            "error": f"Skill '{skill_name}' found in DB but has no content.",
                            "skill_id": skill.get("id"),
                            "description": skill.get("description"),
                        })
                    return _render_skill_md_from_db({
                        "name": skill.get("name", ""),
                        "description": skill.get("description", ""),
                        "trigger_keywords": skill.get("trigger_keywords", []),
                        "always_active": skill.get("always_active", False),
                        "content": content,
                    })

    return json.dumps({"error": f"Skill '{skill_name}' not found."})


def _render_skill_md_from_db(skill: dict) -> str:
    """Build a SKILL.md body from a DB skill entry (preserving YAML frontmatter
    conventions used by agent frameworks)."""
    name = skill.get("name", "unknown")
    description = skill.get("description", "")
    trigger_keywords = skill.get("trigger_keywords", [])
    always_active = skill.get("always_active", False)
    content = skill.get("content", "")

    lines = [
        "# SKILL.md",
        "---",
        f'name: "{name}"',
        f'description: "{description}"',
        "---",
        "",
        "## Purpose",
        "",
        content or description,
    ]

    if trigger_keywords:
        lines.append("")
        lines.append("## Trigger Keywords")
        for kw in trigger_keywords:
            lines.append(f"- {kw}")

    if always_active:
        lines.append("")
        lines.append("## Load Mode")
        lines.append("Always active — part of the agent's core disposition.")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run("stdio")
