import logging
from pathlib import Path
import sys
# Ensure the project root (d:/AAA) is on sys.path so `backend` can be imported
sys.path.append(str(Path(__file__).parent.parent))
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

server_cfg = config.get("server", {})
host = server_cfg.get("host", "127.0.0.1")
port = server_cfg.get("port", 8000)
BASE_URL = f"http://{host}:{port}/api"

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
    
    async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
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
            "conversation_id": conversation_id or ""
        }
        
        try:
            r = await client.post(f"{BASE_URL}/chat", json=chat_payload)
            r.raise_for_status()
            res_data = r.json()
        except Exception as e:
            return f"Error: Failed to generate response from AAA backend. (Details: {e})"

        new_conversation_id = res_data.get("conversation_id")
        content = res_data.get("content", "")
        thinking = res_data.get("thinking", "")

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
        
        return "\n\n".join(output_parts)


@mcp.resource("aaa://philosophy")
async def get_philosophy() -> str:
    """Get the conceptual foundations and philosophical commitments of the Autopoietic Agentic Assemblage."""
    philosophy_path = Path(__file__).parent.parent / "docs" / "PHILOSOPHY.md"
    if philosophy_path.exists():
        try:
            return philosophy_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading philosophy document: {e}"
    return "Philosophy document not found at docs/PHILOSOPHY.md"


@mcp.resource("aaa://identity")
async def get_identity() -> str:
    """Get the identity, voice, traits, and belief configuration of Symbia."""
    identity_path = Path(__file__).parent / "personality" / "identity.yaml"
    if identity_path.exists():
        try:
            return identity_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading identity configuration: {e}"
    return "Identity configuration not found at backend/personality/identity.yaml"


@mcp.resource("aaa://metrics")
async def get_metrics() -> str:
    """Get the current homeostatic and vitality metrics of the assemblage."""
    async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
        try:
            r = await client.get(f"{BASE_URL}/metrics")
            r.raise_for_status()
            import json
            return json.dumps(r.json(), indent=2)
        except Exception as e:
            return f"Error: Failed to fetch metrics from AAA backend. (Details: {e})"


if __name__ == "__main__":
    mcp.run("stdio")
