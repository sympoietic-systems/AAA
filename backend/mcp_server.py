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

@mcp.tool()
async def consult_aaa(message: str, agent_name: str) -> str:
    """
    Send a message/code to Symbia (the AAA posthuman curatorial entity) to check implementation logic,
    discuss theoretical grounding, or confirm alignment with the system's philosophical commitments.

    Arguments:
        message: The inquiry, code block, or philosophical question to present to Symbia.
        agent_name: The name of the calling dev agent (e.g., 'antigravity', 'opencode') to ensure a persistent, dedicated conversation.
    """
    target_title = f"Consultation: {agent_name}"
    
    async with _mkclient(timeout=300.0, trust_env=False) as client:
        # 1. Look up existing conversations to find the dedicated one for this agent
        conversation_id = None
        try:
            r = await client.get(f"{BASE_URL}/conversations")
            r.raise_for_status()
            conversations = r.json().get("conversations", [])
            for c in conversations:
                if c.get("title") == target_title:
                    conversation_id = c.get("id")
                    break
        except Exception as e:
            return f"Error: Failed to connect to AAA backend at {BASE_URL}. Ensure the backend server is running. (Details: {e})"

        # 2. Send the message to the conversation
        chat_payload = {
            "content": message,
            "speaker": "human",
            "conversation_id": conversation_id or "",
            "include_structural_scoring": False,
            "max_tokens": 16384,
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

        # 3. If this was a new conversation, set its title so we can find it next time
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
            for c in conversations:
                if c.get("title") == target_title:
                    conversation_id = c.get("id")
                    break
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


if __name__ == "__main__":
    mcp.run("stdio")
